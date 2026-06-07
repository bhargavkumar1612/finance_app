import { test, expect } from '@playwright/test';
import { confirmChatExpense, loginViaUi, navigateViaSidebar } from '../../fixtures/helpers';

test.describe('@regression transactions filters', () => {
  test('REG-H002 REG-H003: spending and income filters are available', async ({ page }) => {
    await loginViaUi(page, `filters-${Date.now()}@local.test`);
    await confirmChatExpense(page, 'add 250 for lunch');

    await navigateViaSidebar(page, 'Transactions');
    await expect(page.getByRole('heading', { name: 'Transactions' })).toBeVisible({ timeout: 15_000 });

    const typeFilter = page.getByLabel('Type');
    await typeFilter.selectOption('spending');
    await expect(page.getByText(/lunch/i)).toBeVisible();

    await typeFilter.selectOption('income');
    await expect(page.getByText(/lunch/i)).not.toBeVisible();
  });
});
