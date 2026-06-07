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

async function isMobileNav(page: Page): Promise<boolean> {
  return page.locator('#app-nav-toggle').isVisible();
}

/** Open the app navigation drawer on mobile (no-op on desktop). */
export async function openAppNav(page: Page): Promise<void> {
  const toggle = page.locator('#app-nav-toggle');
  if (!(await toggle.isVisible())) return;
  const expanded = await toggle.getAttribute('aria-expanded');
  if (expanded !== 'true') {
    await safeClick(page, toggle);
  }
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('#app-nav-drawer')).toBeVisible();
}

/** Close the app navigation drawer on mobile (no-op on desktop). */
export async function closeAppNav(page: Page): Promise<void> {
  const toggle = page.locator('#app-nav-toggle');
  if (!(await toggle.isVisible())) return;
  const expanded = await toggle.getAttribute('aria-expanded');
  if (expanded === 'true') {
    const backdrop = page.getByRole('button', { name: 'Close navigation menu' });
    await safeClick(page, backdrop);
  }
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
}

export async function navigateViaSidebar(
  page: Page,
  label: 'Chat' | 'Accounts' | 'Transactions' | 'Settings',
): Promise<void> {
  if (await isMobileNav(page)) {
    await openAppNav(page);
  }
  const link = page.getByRole('link', { name: label });
  await link.scrollIntoViewIfNeeded();
  await safeClick(page, link);
  if (label === 'Chat') await expect(page).toHaveURL(/\/chat/);
  if (label === 'Accounts') await expect(page).toHaveURL(/\/accounts/);
  if (label === 'Transactions') await expect(page).toHaveURL(/\/transactions/);
  if (label === 'Settings') await expect(page).toHaveURL(/\/settings/);
  if (await isMobileNav(page)) {
    await expect(page.locator('#app-nav-toggle')).toHaveAttribute('aria-expanded', 'false');
  }
}

export async function logoutViaSidebar(page: Page): Promise<void> {
  await openAppNav(page);
  await openUserMenu(page);
  await safeClick(page, page.getByRole('menuitem', { name: 'Log out' }));
  await expect(page).toHaveURL(/\/login/);
}

/** Open the signed-in user menu in the sidebar footer. */
export async function openUserMenu(page: Page): Promise<void> {
  await openAppNav(page);
  await safeClick(page, page.locator('#user-menu-trigger'));
  await expect(page.getByRole('menu')).toBeVisible();
}

export async function goToSettings(page: Page): Promise<void> {
  await navigateViaSidebar(page, 'Settings');
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
}

export async function selectThemePack(page: Page, label: string): Promise<void> {
  await safeClick(page, page.getByRole('button', { name: new RegExp(label, 'i') }));
}

export async function selectDensity(page: Page, label: 'Comfortable' | 'Compact'): Promise<void> {
  await safeClick(page, page.getByRole('button', { name: new RegExp(`^${label}`, 'i') }));
}

export async function selectFontMode(page: Page, label: 'Theme default' | 'Custom'): Promise<void> {
  await safeClick(page, page.getByRole('button', { name: new RegExp(`^${label}`, 'i') }));
}

export async function selectFontFamily(page: Page, label: string): Promise<void> {
  await safeClick(page, page.getByRole('button', { name: new RegExp(label, 'i') }));
}

export async function selectFontSize(page: Page, label: 'Small' | 'Medium' | 'Large'): Promise<void> {
  await safeClick(page, page.getByRole('button', { name: new RegExp(`^${label}`, 'i') }));
}

export interface ThemePrefsStored {
  themePack: string;
  density: string;
  fontMode?: string;
  fontFamily?: string;
  fontSize?: string;
}

export async function getThemePrefs(page: Page): Promise<ThemePrefsStored | null> {
  return page.evaluate(() => {
    const raw = localStorage.getItem('fc_prefs');
    if (!raw) return null;
    try {
      return JSON.parse(raw) as ThemePrefsStored;
    } catch {
      return null;
    }
  });
}

/** Read computed font-family from html (where typography is applied). */
export async function getComputedRootFontFamily(page: Page): Promise<string> {
  return page.evaluate(() => getComputedStyle(document.documentElement).fontFamily);
}

/** Read computed font-size from html in pixels. */
export async function getComputedRootFontSizePx(page: Page): Promise<number> {
  return page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
}

/** Open chat session history drawer on mobile (no-op on desktop). */
export async function openChatSessions(page: Page): Promise<void> {
  const toggle = page.locator('#chat-sessions-toggle');
  if (!(await toggle.isVisible())) return;
  const expanded = await toggle.getAttribute('aria-expanded');
  if (expanded !== 'true') {
    await safeClick(page, toggle);
  }
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('#chat-sessions-drawer')).toBeVisible();
}

/** Close chat session history drawer on mobile (no-op on desktop). */
export async function closeChatSessions(page: Page): Promise<void> {
  const toggle = page.locator('#chat-sessions-toggle');
  if (!(await toggle.isVisible())) return;
  const expanded = await toggle.getAttribute('aria-expanded');
  if (expanded === 'true') {
    const backdrop = page.getByRole('button', { name: 'Close chat sessions' });
    await safeClick(page, backdrop);
  }
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
}

export async function selectLinkedBankAccount(page: Page, accountName: string): Promise<void> {
  const select = page.locator('#acc-parent');
  const value = await select.locator('option').filter({ hasText: accountName }).first().getAttribute('value');
  if (!value) {
    throw new Error(`No linked bank option matching "${accountName}"`);
  }
  await select.selectOption(value);
}

export async function createBankAccount(
  page: Page,
  name: string,
  institution = 'HDFC',
  openingBalance?: number,
): Promise<void> {
  await page.goto('/accounts');
  await safeClick(page, page.getByRole('button', { name: 'Add account' }));
  await page.locator('#acc-name').fill(name);
  if (institution) {
    await page.locator('#acc-inst').fill(institution);
  }
  if (openingBalance != null) {
    await page.locator('#acc-opening-balance').fill(String(openingBalance));
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
