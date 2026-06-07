import { test, expect } from '@playwright/test';
import { loginViaUi, navigateViaSidebar, rejectChatExpense, safeClick, sendChatMessage } from '../../fixtures/helpers';

test.describe('@regression chat confirm', () => {
  test('REG-C001 REG-C002: expense preview then confirm saves to ledger', async ({ page }) => {
    await loginViaUi(page, `chat-confirm-${Date.now()}@local.test`);
    await page.goto('/chat');
    await sendChatMessage(page, 'add 500 for Swiggy');

    await expect(page.getByText('Confirm transaction')).toBeVisible({ timeout: 45_000 });
    await safeClick(page, page.locator('button.btn-success').filter({ hasText: 'Confirm' }));
    await expect(page.getByText('Saved')).toBeVisible({ timeout: 30_000 });

    await navigateViaSidebar(page, 'Transactions');
    await expect(page.getByRole('heading', { name: 'Transactions' })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('table tbody').getByText('Swiggy')).toBeVisible({ timeout: 15_000 });
  });

  test('REG-C003: cancel does not save transaction', async ({ page }) => {
    await loginViaUi(page, `chat-cancel-${Date.now()}@local.test`);
    await rejectChatExpense(page, 'add 999 for test cancel coffee');

    await navigateViaSidebar(page, 'Transactions');
    await expect(page.getByRole('heading', { name: 'Transactions' })).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('table tbody').getByText(/test cancel coffee/i)).toHaveCount(0);
  });
});
