import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick } from '../../fixtures/helpers';

test.describe('@regression accounts opening balance', () => {
  test('REG-F027 REG-F036: create bank with opening balance shows on card', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `ob-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(`Savings ${suffix}`);
    await page.locator('#acc-inst').fill('HDFC');
    await page.locator('#acc-opening-balance').fill('50000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(`Savings ${suffix}`)).toBeVisible();
    await expect(page.getByText(/Balance ₹50,000/)).toBeVisible();
  });
});
