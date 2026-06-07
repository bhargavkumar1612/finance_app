import { test, expect } from '@playwright/test';
import {
  loginViaUi,
  safeClick,
  selectLinkedBankAccount,
  sendChatMessage,
  waitForChatReady,
} from '../../fixtures/helpers';

async function openAddAccountForm(page: import('@playwright/test').Page) {
  await page.goto('/accounts');
  await expect(page.getByRole('heading', { name: 'Accounts' })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('.spinner')).toHaveCount(0, { timeout: 30_000 });
  const nameInput = page.locator('#acc-name');
  if (!(await nameInput.isVisible())) {
    await safeClick(page, page.getByRole('button', { name: 'Add account' }).first());
  }
  await expect(nameInput).toBeVisible({ timeout: 15_000 });
}

async function submitAccountForm(page: import('@playwright/test').Page) {
  await safeClick(page, page.getByRole('button', { name: 'Create account' }));
  await expect(page.locator('#acc-name')).toBeHidden({ timeout: 15_000 });
}

test.describe('@regression chat investments Slice 1', () => {
  test('REG-C010: portfolio dashboard after MF account setup', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Chat Bank ${suffix}`;
    const mfName = `Chat MF ${suffix}`;
    await loginViaUi(page, `chat-inv-${suffix}@local.test`);

    await openAddAccountForm(page);
    await page.locator('#acc-name').fill(bankName);
    await submitAccountForm(page);

    await openAddAccountForm(page);
    await page.locator('#acc-type').selectOption('mutual_fund');
    await page.locator('#acc-name').fill(mfName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-invested').fill('100000');
    await page.locator('#acc-current').fill('125000');
    await submitAccountForm(page);
    await expect(page.getByText(mfName)).toBeVisible();

    await page.goto('/chat');
    await waitForChatReady(page);
    await sendChatMessage(page, 'how are my investments?');

    await expect(page.getByText('Investment portfolio')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/₹1,25,000/).first()).toBeVisible();
    await expect(page.getByText(/P&L/).first()).toBeVisible();
  });

  test('REG-C011: SIP status card in chat', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `SIP Bank ${suffix}`;
    const sipName = `Chat SIP ${suffix}`;
    await loginViaUi(page, `chat-sip-${suffix}@local.test`);

    await openAddAccountForm(page);
    await page.locator('#acc-name').fill(bankName);
    await submitAccountForm(page);

    await openAddAccountForm(page);
    await page.locator('#acc-type').selectOption('mutual_fund');
    await page.locator('#acc-name').fill(sipName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-mf-mode').selectOption('sip');
    await page.locator('#acc-sip-amount').fill('5000');
    await page.locator('#acc-sip-day').fill('10');
    await page.locator('#acc-sip-start').fill('2025-01-10');
    await page.locator('#acc-sip-tenure').fill('12');
    await submitAccountForm(page);
    await expect(page.getByText(sipName)).toBeVisible();

    await page.goto('/chat');
    await sendChatMessage(page, 'did I pay my SIP this month?');

    await expect(page.getByText('SIP status')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(sipName)).toBeVisible();
    await expect(page.getByText(/Pending this month|Already paid in/)).toBeVisible();
  });

  test('REG-C012: investment allocation pie in chat', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Alloc Bank ${suffix}`;
    const mfName = `Alloc MF ${suffix}`;
    await loginViaUi(page, `chat-alloc-${suffix}@local.test`);

    await openAddAccountForm(page);
    await page.locator('#acc-name').fill(bankName);
    await submitAccountForm(page);

    await openAddAccountForm(page);
    await page.locator('#acc-type').selectOption('mutual_fund');
    await page.locator('#acc-name').fill(mfName);
    await selectLinkedBankAccount(page, bankName);
    await page.locator('#acc-opening-balance').fill('50000');
    await submitAccountForm(page);

    await page.goto('/chat');
    await sendChatMessage(page, 'show my investment allocation');

    await expect(page.getByText('Investment allocation')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/₹50,000/).first()).toBeVisible();
  });
});
