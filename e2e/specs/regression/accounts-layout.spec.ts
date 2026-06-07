import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick, selectLinkedBankAccount } from '../../fixtures/helpers';

test.describe('@regression accounts layout', () => {
  test('REG-F053: hero shows net worth, assets, and liabilities sections', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `layout-hero-${suffix}@local.test`);
    await page.goto('/accounts');

    await expect(page.locator('#accounts-hero')).toBeVisible();
    await expect(page.locator('#accounts-hero')).toContainText('Net worth');
    await expect(page.locator('#accounts-section-assets')).toBeVisible();
    await expect(page.locator('#accounts-section-liabilities')).toBeVisible();
  });

  test('REG-F054: accounts appear in correct asset and liability sub-groups', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Layout Bank ${suffix}`;
    const ccName = `Layout CC ${suffix}`;
    await loginViaUi(page, `layout-groups-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await page.locator('#acc-opening-balance').fill('100000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('credit_card');
    await page.locator('#acc-name').fill(ccName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-limit').fill('200000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.locator('#accounts-group-cash-wallets')).toContainText(bankName);
    await expect(page.locator('#accounts-group-credit-cards')).toContainText(ccName);
    await expect(page.locator('#accounts-group-cash-wallets')).not.toContainText(ccName);
  });

  test('REG-F055: type dropdown grouped and placement hint updates', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `layout-form-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await expect(page.locator('#acc-type-hint')).toContainText('Assets → Cash & wallets');

    await page.locator('#acc-type').selectOption('mutual_fund');
    await expect(page.locator('#acc-type-hint')).toContainText('Assets → Investments');

    await page.locator('#acc-type').selectOption('loan');
    await expect(page.locator('#acc-type-hint')).toContainText('Liabilities → Loans');
  });
});
