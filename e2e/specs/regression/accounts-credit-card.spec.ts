import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick, selectLinkedBankAccount } from '../../fixtures/helpers';

test.describe('@regression accounts credit card', () => {
  test('REG-F001 REG-F011 REG-F012: create bank then credit card with linked parent', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `HDFC Savings ${suffix}`;
    await loginViaUi(page, `accounts-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await page.locator('#acc-inst').fill('HDFC');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));
    await expect(page.getByText(bankName)).toBeVisible();

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('credit_card');
    await page.locator('#acc-name').fill(`HDFC Regalia ${suffix}`);
    await page.locator('#acc-inst').fill('HDFC');
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-limit').fill('800000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(`HDFC Regalia ${suffix}`)).toBeVisible();
    await expect(page.getByText(new RegExp(`linked to ${bankName}`))).toBeVisible();
  });

  test('REG-F046: create credit card with statement due day', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `ICICI Savings ${suffix}`;
    await loginViaUi(page, `cc-due-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('credit_card');
    await page.locator('#acc-name').fill(`ICICI Coral ${suffix}`);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-cc-due').fill('15');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(`ICICI Coral ${suffix}`)).toBeVisible();
    await expect(page.getByText(/Statement due day 15/)).toBeVisible();
  });

  test('REG-F056: create credit card with initial credit used and as-of date', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `CC Initial Bank ${suffix}`;
    const ccName = `CC Initial ${suffix}`;
    await loginViaUi(page, `cc-initial-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('credit_card');
    await page.locator('#acc-name').fill(ccName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-initial-used').fill('35000');
    await page.locator('#acc-initial-used-date').fill('2026-05-15');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(ccName)).toBeVisible();
    await expect(page.getByText(/Used ₹35,000/)).toBeVisible();
  });
});
