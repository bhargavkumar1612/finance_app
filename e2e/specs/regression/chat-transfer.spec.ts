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

test.describe('@regression chat transfer Slice 3', () => {
  test('REG-C030: dual-leg SIP transfer confirm flow', async ({ page }) => {
    const suffix = Date.now();
    const bankName = `Xfer Bank ${suffix}`;
    const sipName = `Xfer SIP ${suffix}`;

    await loginViaUi(page, `chat-xfer-${suffix}@local.test`);

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
    await waitForChatReady(page);
    await sendChatMessage(page, `record SIP 5000 for ${sipName}`);

    await expect(page.getByText('Confirm transfer')).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(bankName).first()).toBeVisible();
    await expect(page.getByText(sipName).first()).toBeVisible();

    await safeClick(page, page.getByRole('button', { name: 'Confirm' }).first());

    await expect(page.getByText(/Recorded SIP transfer|Recorded in your ledger/i).first()).toBeVisible({
      timeout: 30_000,
    });
  });
});
