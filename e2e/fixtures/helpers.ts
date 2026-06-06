import { Locator, Page, expect } from '@playwright/test';
import { uniqueEmail } from './data';

/** Log in via UI (Enter submit avoids Next.js dev overlay blocking clicks). */
export async function loginViaUi(page: Page, email?: string): Promise<string> {
  const userEmail = email ?? uniqueEmail();
  await page.goto('/login');
  const input = page.getByPlaceholder('user@example.com');
  await input.fill(userEmail);
  await input.press('Enter');
  await expect(page).toHaveURL(/\/chat/);
  await waitForChatReady(page);
  return userEmail;
}

/** Chat shell is ready when input is visible (not stuck on Loading/build error). */
export async function waitForChatReady(page: Page): Promise<void> {
  await expect(page.locator('#chat-input')).toBeVisible({ timeout: 30_000 });
}

export async function sendChatMessage(page: Page, message: string): Promise<void> {
  await waitForChatReady(page);
  const input = page.locator('#chat-input');
  await input.fill(message);
  await input.press('Enter');
}

/** Prefer force click — Next.js dev overlay can intercept pointer events in dev mode. */
export async function safeClick(_page: Page, locator: Locator): Promise<void> {
  await locator.click({ force: true });
}

export async function createBankAccount(
  page: Page,
  name: string,
  institution = 'HDFC',
): Promise<void> {
  await page.goto('/accounts');
  await safeClick(page, page.getByRole('button', { name: 'Add account' }));
  await page.locator('#acc-name').fill(name);
  if (institution) {
    await page.locator('#acc-inst').fill(institution);
  }
  await safeClick(page, page.getByRole('button', { name: 'Create account' }));
  await expect(page.getByText(name, { exact: false })).toBeVisible();
}

export async function confirmChatExpense(page: Page, message: string): Promise<void> {
  await page.goto('/chat');
  await sendChatMessage(page, message);
  await expect(page.getByText('Confirm transaction')).toBeVisible({ timeout: 45_000 });
  await safeClick(page, page.locator('button.btn-success').filter({ hasText: 'Confirm' }));
  await expect(page.getByText('Saved')).toBeVisible({ timeout: 30_000 });
}

export async function rejectChatExpense(page: Page, message: string): Promise<void> {
  await page.goto('/chat');
  await sendChatMessage(page, message);
  await expect(page.getByText('Confirm transaction')).toBeVisible({ timeout: 45_000 });
  await safeClick(page, page.locator('button.btn-ghost').filter({ hasText: 'Cancel' }).first());
}
