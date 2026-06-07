import { test, expect } from '@playwright/test';
import {
  loginViaUi,
  navigateViaSidebar,
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

test.describe('@regression chat obligations Slice 2', () => {
  test('REG-C020: obligations card shows SIP and loan sections', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Oblig Bank ${suffix}`;
    const sipName = `Oblig SIP ${suffix}`;
    const loanBankName = `Loan Bank ${suffix}`;
    const loanName = `Home Loan ${suffix}`;

    await loginViaUi(page, `chat-oblig-${suffix}@local.test`);

    // Create SIP mutual fund
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

    // Create loan account
    await openAddAccountForm(page);
    await page.locator('#acc-name').fill(loanBankName);
    await submitAccountForm(page);

    await openAddAccountForm(page);
    await page.locator('#acc-type').selectOption('loan');
    await page.locator('#acc-name').fill(loanName);
    await selectLinkedBankAccount(page, loanBankName);
    await page.locator('#acc-emi').fill('25000');
    await page.locator('#acc-tenure').fill('240');
    await page.locator('#acc-loan-start').fill('2020-01-05');
    await submitAccountForm(page);
    await expect(page.getByText(loanName).first()).toBeVisible();

    // Ask chat
    await page.goto('/chat');
    await waitForChatReady(page);
    await sendChatMessage(page, "what's due this month?");

    await expect(page.getByText('Upcoming obligations').first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(sipName).first()).toBeVisible();
    await expect(page.getByText(loanName).first()).toBeVisible();
  });

  test('REG-C021: recurring bill confirm flow via chat', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `chat-rbill-${suffix}@local.test`);

    await page.goto('/chat');
    await waitForChatReady(page);
    await sendChatMessage(page, 'add recurring bill Netflix 499');

    await expect(page.getByText('Confirm recurring bill')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText('Netflix').first()).toBeVisible();

    // Click confirm button on the card
    await safeClick(page, page.getByRole('button', { name: 'Confirm' }).first());

    await expect(page.getByText(/Recurring bill added|Netflix/i).first()).toBeVisible({ timeout: 30_000 });
  });

  test('REG-C022: persona settings round-trip', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `persona-${suffix}@local.test`);

    await navigateViaSidebar(page, 'Settings');
    await expect(page.getByRole('heading', { name: 'Financial persona' })).toBeVisible({ timeout: 15_000 });

    const textarea = page.getByRole('textbox', { name: /Financial persona notes/i });
    await expect(textarea).toBeVisible();
    await textarea.fill('SIP-heavy investor. Salary on 1st.');

    await safeClick(page, page.getByRole('button', { name: 'Save persona' }));

    await expect(page.getByText('Persona saved.')).toBeVisible({ timeout: 15_000 });

    // Reload and verify persistence
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Financial persona' })).toBeVisible({ timeout: 15_000 });
    const reloaded = page.getByRole('textbox', { name: /Financial persona notes/i });
    await expect(reloaded).toHaveValue('SIP-heavy investor. Salary on 1st.');
  });
});
