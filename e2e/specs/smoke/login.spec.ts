import { test, expect } from '@playwright/test';
import { loginViaUi } from '../../fixtures/auth';

test.describe('@smoke login', () => {
  test('REG-A002: login redirects to chat', async ({ page }) => {
    await loginViaUi(page, `login-${Date.now()}@local.test`);
    await expect(page.locator('#chat-input')).toBeVisible();
    await expect(page.getByText('Your AI finance assistant')).toBeVisible();
  });
});
