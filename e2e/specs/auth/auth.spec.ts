import { expect, test } from '@playwright/test';
import {
  DEFAULT_PASSWORD,
  approveUserViaApi,
  loginAsSuperAdmin,
  loginViaUi,
  loginWithCredentials,
  registerViaUi,
  uniqueUsername,
} from '../../fixtures/auth';

test.describe('Auth + super admin (Round 9)', () => {
  // REG-A1 — registration creates a pending account that cannot log in yet.
  test('REG-A1: register is gated behind approval', async ({ page }) => {
    const username = uniqueUsername('rega1');
    await registerViaUi(page, username, DEFAULT_PASSWORD);
    await expect(page.locator('#register-success')).toContainText(/pending/i);

    // Pending user cannot log in.
    await page.goto('/login');
    await page.locator('#login-username').fill(username);
    const pw = page.locator('#login-password');
    await pw.fill(DEFAULT_PASSWORD);
    await pw.press('Enter');
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText(/pending administrator approval/i)).toBeVisible();
  });

  // REG-A2 — super admin approval unblocks login (the full happy path). @smoke
  test('REG-A2: approved user can log in @smoke', async ({ page }) => {
    const username = uniqueUsername('rega2');
    await registerViaUi(page, username, DEFAULT_PASSWORD);
    await approveUserViaApi(page, username);
    await loginWithCredentials(page, username, DEFAULT_PASSWORD);
    await expect(page).toHaveURL(/\/chat/);
  });

  // REG-A3 — forgot-password shows a generic queued message (no enumeration).
  test('REG-A3: forgot password requests a manual reset', async ({ page }) => {
    const username = await loginViaUi(page); // registered + approved
    await page.goto('/forgot-password');
    await page.locator('#forgot-username').fill(username);
    await page.locator('#forgot-submit').click({ force: true });
    await expect(page.locator('#forgot-success')).toBeVisible();
  });

  // REG-A4 — normal users have no Admin nav and cannot reach /admin.
  test('REG-A4: non-admin is redirected away from /admin', async ({ page }) => {
    await loginViaUi(page);
    await expect(page.getByRole('link', { name: 'Admin' })).toHaveCount(0);
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/chat/);
  });

  // REG-A5 — super admin sees the admin page and can approve a pending signup via UI.
  test('REG-A5: super admin approves a pending signup from /admin', async ({ page }) => {
    const username = uniqueUsername('rega5');
    await registerViaUi(page, username, DEFAULT_PASSWORD);

    await loginAsSuperAdmin(page);
    await page.goto('/admin');
    await expect(page.locator('#admin-user-count')).toBeVisible();

    const row = page.locator('#admin-pending-signups tr', { hasText: username });
    await expect(row).toBeVisible();
    await row.getByRole('button', { name: 'Approve' }).click();
    await expect(page.locator('#admin-pending-signups tr', { hasText: username })).toHaveCount(0);

    // The approved user can now log in.
    await loginWithCredentials(page, username, DEFAULT_PASSWORD);
    await expect(page).toHaveURL(/\/chat/);
  });
});
