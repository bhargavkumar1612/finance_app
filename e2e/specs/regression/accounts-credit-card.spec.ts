import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick } from '../../fixtures/helpers';

test.describe('@regression accounts', () => {
  test('REG-F001 REG-F011 REG-F012: create bank then credit card with linked parent', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `accounts-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(`HDFC Savings ${suffix}`);
    await page.locator('#acc-inst').fill('HDFC');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));
    await expect(page.getByText(`HDFC Savings ${suffix}`)).toBeVisible();

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('credit_card');
    await page.locator('#acc-name').fill(`HDFC Regalia ${suffix}`);
    await page.locator('#acc-inst').fill('HDFC');
    await page.locator('#acc-parent').selectOption({ label: `HDFC Savings ${suffix} (Bank)` });
    await page.locator('#acc-limit').fill('800000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(`HDFC Regalia ${suffix}`)).toBeVisible();
    await expect(page.getByText(new RegExp(`linked to HDFC Savings ${suffix}`))).toBeVisible();
  });
});
