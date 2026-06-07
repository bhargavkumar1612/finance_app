import { test, expect } from '@playwright/test';
import {
  getComputedRootFontFamily,
  getComputedRootFontSizePx,
  getThemePrefs,
  goToSettings,
  loginViaUi,
  openAppNav,
  openUserMenu,
  selectDensity,
  selectFontFamily,
  selectFontMode,
  selectFontSize,
  selectThemePack,
} from '../../fixtures/helpers';

test.describe('@regression @look-and-feel settings look and feel', () => {
  test('REG-S007: compact density persists and applies data-density', async ({ page }) => {
    await loginViaUi(page, `lf-s007-${Date.now()}@local.test`);
    await goToSettings(page);

    await selectDensity(page, 'Compact');
    await expect(page.getByRole('button', { name: /^Compact/i })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('html')).toHaveAttribute('data-density', 'compact');

    const prefs = await getThemePrefs(page);
    expect(prefs?.density).toBe('compact');

    await page.reload();
    await expect(page.getByRole('button', { name: /^Compact/i })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('html')).toHaveAttribute('data-density', 'compact');
  });

  test('REG-S008: each theme pack applies data-theme on html', async ({ page }) => {
    await loginViaUi(page, `lf-s008-${Date.now()}@local.test`);
    await goToSettings(page);

    const packs = [
      { label: 'Paper', id: 'paper' },
      { label: 'Coral', id: 'coral' },
      { label: 'Midnight', id: 'midnight' },
      { label: 'Slate', id: 'slate' },
    ];

    for (const pack of packs) {
      await selectThemePack(page, pack.label);
      await expect(page.locator('html')).toHaveAttribute('data-theme', pack.id);
      const prefs = await getThemePrefs(page);
      expect(prefs?.themePack).toBe(pack.id);
    }
  });

  test('REG-S009: user menu navigates to settings', async ({ page }, testInfo) => {
    await loginViaUi(page, `lf-s009-${Date.now()}@local.test`);
    if (testInfo.project.name === 'mobile-chrome') {
      await openAppNav(page);
    }

    await openUserMenu(page);
    await page.getByRole('menuitem', { name: 'Settings' }).click();

    await expect(page).toHaveURL(/\/settings/);
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  });

  test('REG-ML008: mobile compact density persists after reload', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile-chrome', 'Mobile-only test');

    await loginViaUi(page, `lf-ml008-${Date.now()}@local.test`);
    await goToSettings(page);

    await selectDensity(page, 'Compact');
    await expect(page.locator('html')).toHaveAttribute('data-density', 'compact');

    await page.reload();
    await expect(page.getByRole('button', { name: /^Compact/i })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('html')).toHaveAttribute('data-density', 'compact');
  });

  test('REG-S010: theme default font changes with theme; custom font persists', async ({ page }) => {
    await loginViaUi(page, `lf-s010-${Date.now()}@local.test`);
    await goToSettings(page);

    await selectThemePack(page, 'Coral');
    await expect(page.locator('html')).toHaveAttribute('data-font', 'lora');
    await expect.poll(() => getComputedRootFontFamily(page)).toMatch(/lora/i);

    await selectThemePack(page, 'Midnight');
    await expect(page.locator('html')).toHaveAttribute('data-font', 'geist');
    await expect.poll(() => getComputedRootFontFamily(page)).toMatch(/geist/i);

    await selectFontMode(page, 'Custom');
    await selectFontFamily(page, 'JetBrains Mono');
    await expect(page.locator('html')).toHaveAttribute('data-font', 'jetbrains-mono');
    await expect(page.locator('html')).toHaveAttribute('data-font-mode', 'custom');
    await expect.poll(() => getComputedRootFontFamily(page)).toMatch(/jetbrains mono/i);

    await selectThemePack(page, 'Paper');
    await expect(page.locator('html')).toHaveAttribute('data-font', 'jetbrains-mono');
    await expect.poll(() => getComputedRootFontFamily(page)).toMatch(/jetbrains mono/i);

    const prefs = await getThemePrefs(page);
    expect(prefs?.fontMode).toBe('custom');
    expect(prefs?.fontFamily).toBe('jetbrains-mono');
  });

  test('REG-S011: text size applies data-font-size and persists', async ({ page }) => {
    await loginViaUi(page, `lf-s011-${Date.now()}@local.test`);
    await goToSettings(page);

    const mediumSize = await getComputedRootFontSizePx(page);

    await selectFontSize(page, 'Large');
    await expect(page.locator('html')).toHaveAttribute('data-font-size', 'large');
    await expect.poll(async () => getComputedRootFontSizePx(page)).toBeGreaterThan(mediumSize);

    const prefs = await getThemePrefs(page);
    expect(prefs?.fontSize).toBe('large');

    await page.reload();
    await expect(page.getByRole('button', { name: /^Large/i })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('html')).toHaveAttribute('data-font-size', 'large');
    await expect.poll(async () => getComputedRootFontSizePx(page)).toBeGreaterThan(mediumSize);
  });

  test('REG-S012: settings shows mobile access QR after entering LAN URL', async ({ page }) => {
    await loginViaUi(page, `lf-s012-${Date.now()}@local.test`);
    await goToSettings(page);

    await expect(page.getByRole('heading', { name: 'Open on phone' })).toBeVisible();
    await page.getByPlaceholder('e.g. http://192.168.1.2:3000').fill('http://192.168.1.2:3000');

    await expect(page.getByText('http://192.168.1.2:3000')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Copy link' })).toBeVisible();
    await expect(page.locator('svg').first()).toBeVisible();
  });
});
