import { test, expect } from '@playwright/test';
import { loginViaUi } from '../../fixtures/auth';

test.describe('@smoke health', () => {
  test('REG-A008 REG-B001: chat page loads and health proxy works', async ({ page, request }) => {
    await loginViaUi(page, `health-${Date.now()}@local.test`);
    await expect(page.locator('#chat-input')).toBeVisible();

    const health = await request.get('/health');
    expect(health.ok()).toBeTruthy();
    expect(await health.json()).toEqual({ status: 'ok' });
  });
});
