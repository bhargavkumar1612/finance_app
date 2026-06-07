import { test, expect } from '@playwright/test';
import { loginViaUi, sendChatMessage } from '../../fixtures/helpers';

test.describe('@smoke chat investments', () => {
  test('REG-D012: portfolio chat intent returns dashboard card', async ({ page }) => {
    await loginViaUi(page, `smoke-inv-${Date.now()}@local.test`);
    await sendChatMessage(page, 'how are my investments?');
    await expect(page.getByText('Investment portfolio')).toBeVisible({ timeout: 45_000 });
  });
});
