import { test, expect } from '@playwright/test';
import {
  closeAppNav,
  closeChatSessions,
  loginViaUi,
  logoutViaSidebar,
  navigateViaSidebar,
  openAppNav,
  openChatSessions,
  safeClick,
  sendChatMessage,
} from '../../fixtures/helpers';

test.describe('@regression mobile layout', () => {
  test.beforeEach(({ }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chrome', 'Mobile layout tests run on mobile-chrome only');
  });

  test('REG-ML001: app sidebar closed on load; accounts hero fits viewport', async ({ page }) => {
    await loginViaUi(page, `mobile-m001-${Date.now()}@local.test`);
    await page.goto('/accounts');

    await expect(page.locator('#app-nav-toggle')).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('#accounts-hero')).toBeVisible();

    const overflowX = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(overflowX).toBe(false);
  });

  test('REG-ML002: app nav toggle opens and backdrop closes drawer', async ({ page }) => {
    await loginViaUi(page, `mobile-m002-${Date.now()}@local.test`);
    await page.goto('/accounts');

    await openAppNav(page);
    await expect(page.locator('#app-nav-drawer')).toBeVisible();
    await closeAppNav(page);
    await expect(page.locator('#app-nav-toggle')).toHaveAttribute('aria-expanded', 'false');
  });

  test('REG-ML003: sidebar navigation auto-closes drawer', async ({ page }) => {
    await loginViaUi(page, `mobile-m003-${Date.now()}@local.test`);

    await navigateViaSidebar(page, 'Accounts');
    await expect(page.getByRole('heading', { name: 'Accounts' })).toBeVisible();

    await navigateViaSidebar(page, 'Transactions');
    await expect(page.getByRole('heading', { name: 'Transactions' })).toBeVisible();

    await navigateViaSidebar(page, 'Chat');
    await expect(page.locator('#chat-input')).toBeVisible();
  });

  test('REG-ML004: chat sessions drawer toggles and closes on backdrop', async ({ page }) => {
    await loginViaUi(page, `mobile-m004-${Date.now()}@local.test`);
    await page.goto('/chat');

    await expect(page.locator('#chat-sessions-toggle')).toHaveAttribute('aria-expanded', 'false');
    await openChatSessions(page);
    await expect(page.locator('#chat-sessions-drawer')).toBeVisible();
    await closeChatSessions(page);
    await expect(page.locator('#chat-sessions-toggle')).toHaveAttribute('aria-expanded', 'false');
  });

  test('REG-ML004b: new chat closes sessions drawer', async ({ page }) => {
    await loginViaUi(page, `mobile-m004b-${Date.now()}@local.test`);
    await page.goto('/chat');
    await sendChatMessage(page, 'hello mobile sessions');

    await openChatSessions(page);
    await safeClick(page, page.getByRole('button', { name: '+ New Chat' }));
    await expect(page.locator('#chat-sessions-toggle')).toHaveAttribute('aria-expanded', 'false');
  });

  test('REG-ML005: logout via user menu on mobile', async ({ page }) => {
    await loginViaUi(page, `mobile-m005-${Date.now()}@local.test`);
    await logoutViaSidebar(page);
    await expect(page.getByPlaceholder('user@example.com')).toBeVisible();
  });

  test('REG-ML006: root and import redirects', async ({ page }) => {
    await loginViaUi(page, `mobile-m006-${Date.now()}@local.test`);

    await page.goto('/');
    await expect(page).toHaveURL(/\/chat/);

    await page.goto('/import');
    await expect(page).toHaveURL(/\/transactions\?import=1/);
  });

  test('REG-ML007: settings page reachable from mobile nav', async ({ page }) => {
    await loginViaUi(page, `mobile-m007-${Date.now()}@local.test`);
    await navigateViaSidebar(page, 'Settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  });
});
