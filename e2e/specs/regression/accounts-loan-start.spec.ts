import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick, selectLinkedBankAccount } from '../../fixtures/helpers';

test.describe('@regression accounts loan', () => {
  test('REG-F047: loan with EMI and tenure requires start date', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `SBI Savings ${suffix}`;
    await loginViaUi(page, `loan-start-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('loan');
    await page.locator('#acc-loan-type').selectOption('home');
    await page.locator('#acc-name').fill(`Home Loan ${suffix}`);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-emi').fill('40000');
    await page.locator('#acc-tenure').fill('240');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(/Start date is required when EMI and tenure are set/)).toBeVisible();
  });

  test('REG-F048: loan with start date, EMI, and tenure creates successfully', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Axis Savings ${suffix}`;
    const loanName = `Axis Home ${suffix}`;
    await loginViaUi(page, `loan-ok-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('loan');
    await page.locator('#acc-loan-type').selectOption('home');
    await page.locator('#acc-name').fill(loanName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-emi').fill('35000');
    await page.locator('#acc-tenure').fill('180');
    await page.locator('#acc-loan-start').fill('2024-06-01');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(loanName)).toBeVisible();
  });
});
