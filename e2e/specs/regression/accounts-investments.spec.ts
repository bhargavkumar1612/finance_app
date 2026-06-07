import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick, selectLinkedBankAccount } from '../../fixtures/helpers';

test.describe('@regression accounts investments', () => {
  test('REG-F040 REG-F041: create mutual fund with parent and opening balance', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `HDFC Savings ${suffix}`;
    const mfName = `Parag Parikh ${suffix}`;
    await loginViaUi(page, `inv-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await page.locator('#acc-inst').fill('HDFC');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));
    await expect(page.getByText(bankName)).toBeVisible();

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('mutual_fund');
    await expect(page.getByText('Linked bank account')).toBeVisible();
    await page.locator('#acc-name').fill(mfName);
    await page.locator('#acc-inst').fill('Groww');
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-opening-balance').fill('125000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(mfName)).toBeVisible();
    await expect(page.getByText(new RegExp(`linked to ${bankName}`))).toBeVisible();
    await expect(page.getByText(/Invested ₹1,25,000/)).toBeVisible();
    await expect(page.getByText(/Current ₹1,25,000/)).toBeVisible();
    await expect(page.getByText(/P&L \+₹0 \(+0\.0%\)/)).toBeVisible();
  });

  test('REG-F042: create fixed deposit shows planning fields', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `ICICI Bank ${suffix}`;
    const fdName = `ICICI FD ${suffix}`;
    await loginViaUi(page, `fd-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await page.locator('#acc-inst').fill('ICICI');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('fixed_deposit');
    await expect(page.locator('#acc-fd-start')).toBeVisible();
    await expect(page.locator('#acc-fd-tenure')).toBeVisible();
    await expect(page.locator('#acc-fd-rate')).toBeVisible();

    await page.locator('#acc-name').fill(fdName);
    await page.locator('#acc-inst').fill('ICICI');
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-fd-start').fill('2026-01-01');
    await page.locator('#acc-fd-tenure').fill('12');
    await page.locator('#acc-fd-rate').fill('7.25');
    await page.locator('#acc-opening-balance').fill('500000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(fdName)).toBeVisible();
    await expect(page.getByText(/Invested ₹5,00,000/)).toBeVisible();
    await expect(page.getByText(/Current ₹5,00,000/)).toBeVisible();
    await expect(page.getByText(/Matures 2027-01-01/)).toBeVisible();
  });

  test('REG-F060: investment card shows profit when current exceeds invested', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Axis Bank ${suffix}`;
    const mfName = `Growth Fund ${suffix}`;
    await loginViaUi(page, `pnl-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('mutual_fund');
    await page.locator('#acc-name').fill(mfName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-invested').fill('100000');
    await page.locator('#acc-current').fill('125000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(mfName)).toBeVisible();
    await expect(page.getByText(/Invested ₹1,00,000/)).toBeVisible();
    await expect(page.getByText(/Current ₹1,25,000/)).toBeVisible();
    await expect(page.getByText(/P&L \+₹25,000 \(\+25\.0%\)/)).toBeVisible();
  });

  test('REG-F051: create mutual fund with folio number', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Kotak Savings ${suffix}`;
    const mfName = `Nifty Index ${suffix}`;
    await loginViaUi(page, `folio-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('mutual_fund');
    await page.locator('#acc-name').fill(mfName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-folio').fill('9876543210');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(mfName)).toBeVisible();
    await expect(page.getByText(/Folio ••••3210/)).toBeVisible();
  });

  test('REG-F052: create stock with demat ID', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Zerodha Bank ${suffix}`;
    const stockName = `Equity ${suffix}`;
    await loginViaUi(page, `demat-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('stock');
    await page.locator('#acc-name').fill(stockName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-demat').fill('IN3001234567890');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(stockName)).toBeVisible();
    await expect(page.getByText(/Demat ••••7890/)).toBeVisible();
  });

  test('REG-F061: create SIP mutual fund shows installment tracking', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `SIP Bank ${suffix}`;
    const mfName = `Index SIP ${suffix}`;
    await loginViaUi(page, `sip-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-name').fill(bankName);
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('mutual_fund');
    await page.locator('#acc-mf-mode').selectOption('sip');
    await expect(page.locator('#acc-sip-amount')).toBeVisible();
    await page.locator('#acc-name').fill(mfName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-sip-amount').fill('5000');
    await page.locator('#acc-sip-day').fill('10');
    await page.locator('#acc-sip-start').fill('2025-01-10');
    await page.locator('#acc-sip-tenure').fill('12');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(mfName)).toBeVisible();
    await expect(page.getByText(/SIP · ₹5,000\/mo · debit day 10/)).toBeVisible();
    await expect(page.getByText(/Installments 0 paid · 12 pending/)).toBeVisible();
  });
});
