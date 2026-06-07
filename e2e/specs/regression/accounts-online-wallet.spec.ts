import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick } from '../../fixtures/helpers';

test.describe('@regression accounts online wallet', () => {
  test('REG-F014 REG-F033: create standalone online wallet without linked bank', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `wallet-standalone-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('wallet');
    await expect(page.getByText('Linked bank account (optional)')).toBeVisible();
    await page.locator('#acc-name').fill(`Amazon Pay ${suffix}`);
    await page.locator('#acc-inst').fill('Amazon Pay');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(`Amazon Pay ${suffix}`)).toBeVisible();
    await expect(page.getByText(/linked to/i)).not.toBeVisible();
  });

  test('REG-F034: create online wallet with optional linked bank and provider', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `HDFC Savings ${suffix}`;
    await loginViaUi(page, `wallet-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await page.locator('#acc-inst').fill('HDFC');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));
    await expect(page.getByText(bankName)).toBeVisible();

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('wallet');
    await expect(page.getByText('Provider (optional)')).toBeVisible();

    await page.locator('#acc-name').fill(`PhonePe ${suffix}`);
    await page.locator('#acc-inst').fill('PhonePe');
    await page.locator('#acc-parent').selectOption({ label: `${bankName} (Bank)` });
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(`PhonePe ${suffix}`)).toBeVisible();
    await expect(page.getByText(new RegExp(`linked to ${bankName}`))).toBeVisible();
    await expect(page.getByText(/PhonePe/)).toBeVisible();
  });
});
