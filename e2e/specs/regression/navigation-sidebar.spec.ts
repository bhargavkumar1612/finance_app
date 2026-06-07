import { test, expect } from '@playwright/test';
import { loginViaUi, logoutViaSidebar, navigateViaSidebar, openAppNav } from '../../fixtures/helpers';

test.describe('@regression navigation sidebar', () => {
  test('REG-S001: Chat / Accounts / Transactions / Settings links load each page', async ({ page }, testInfo) => {
    await loginViaUi(page, `nav-s001-${Date.now()}@local.test`);

    if (testInfo.project.name === 'mobile-chrome') {
      await navigateViaSidebar(page, 'Chat');
    } else {
      await page.getByRole('link', { name: 'Chat' }).click();
      await expect(page).toHaveURL(/\/chat/);
    }
    await expect(page.locator('#chat-input')).toBeVisible();

    await navigateViaSidebar(page, 'Accounts');
    await expect(page.getByRole('heading', { name: 'Accounts' })).toBeVisible();

    await navigateViaSidebar(page, 'Transactions');
    await expect(page.getByRole('heading', { name: 'Transactions' })).toBeVisible();

    await navigateViaSidebar(page, 'Settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  });

  test('REG-S002: / redirects to /chat', async ({ page }) => {
    await loginViaUi(page, `nav-s002-${Date.now()}@local.test`);
    await page.goto('/');
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.locator('#chat-input')).toBeVisible();
  });

  test('REG-S003: /import redirects to /transactions?import=1', async ({ page }) => {
    await loginViaUi(page, `nav-s003-${Date.now()}@local.test`);
    await page.goto('/import');
    await expect(page).toHaveURL(/\/transactions\?import=1/);
  });

  test('REG-S004: API docs link has correct href', async ({ page }, testInfo) => {
    await loginViaUi(page, `nav-s004-${Date.now()}@local.test`);
    if (testInfo.project.name === 'mobile-chrome') {
      await openAppNav(page);
    }
    const docsLink = page.getByRole('link', { name: 'API Docs ↗' });
    await expect(docsLink).toHaveAttribute('href', 'http://localhost:8000/docs');
    await expect(docsLink).toHaveAttribute('target', '_blank');
  });

  test('REG-A007: logout from user menu clears session', async ({ page }, testInfo) => {
    await loginViaUi(page, `nav-a007-${Date.now()}@local.test`);
    if (testInfo.project.name === 'mobile-chrome') {
      await openAppNav(page);
    }
    await logoutViaSidebar(page);
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByPlaceholder('user@example.com')).toBeVisible();
  });

  test('REG-S005: Settings link loads settings page', async ({ page }, testInfo) => {
    await loginViaUi(page, `nav-s005-${Date.now()}@local.test`);
    await navigateViaSidebar(page, 'Settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Appearance' })).toBeVisible();
  });

  test('REG-S006: theme selection persists after reload', async ({ page }, testInfo) => {
    await loginViaUi(page, `nav-s006-${Date.now()}@local.test`);
    await navigateViaSidebar(page, 'Settings');
    await page.getByRole('button', { name: /Midnight/i }).click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'midnight');
    await page.reload();
    await expect(page.getByRole('button', { name: /Midnight/i })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'midnight');
  });
});
