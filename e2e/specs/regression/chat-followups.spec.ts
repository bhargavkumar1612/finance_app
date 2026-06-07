import { test, expect } from '@playwright/test';
import {
  loginViaUi,
  sendChatMessage,
  waitForChatReady,
  waitForChatResponse,
  copyChatTranscriptFromUi,
} from '../../fixtures/helpers';

const hasOpenRouter = Boolean(process.env.OPENROUTER_API_KEY?.trim());

test.describe('@regression chat copy transcript', () => {
  test('REG-C042: copy whole chat puts transcript on clipboard', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await loginViaUi(page, `chat-copy-${Date.now()}@local.test`);
    await sendChatMessage(page, 'what is my net worth?');
    await waitForChatResponse(page);

    await expect(page.locator('#chat-copy-transcript')).toBeVisible();
    await page.locator('#chat-copy-transcript').click();
    await expect(page.getByText('Copied!')).toBeVisible({ timeout: 5_000 });

    const transcript = await copyChatTranscriptFromUi(page);
    expect(transcript).toContain('Finance Copilot — Chat transcript');
    expect(transcript).toContain('[User]');
    expect(transcript).toContain('what is my net worth?');
    expect(transcript).toContain('[Assistant]');
  });
});

test.describe('@regression @llm chat follow-ups', () => {
  test.skip(
    !hasOpenRouter,
    'Set OPENROUTER_API_KEY and run API with LLM_PROVIDER=openrouter + LLM_PLANNER_MODE=auto',
  );

  test('REG-C040: affordability EMI then salary clarification stays on affordability', async ({ page }) => {
    await loginViaUi(page, `chat-afford-follow-${Date.now()}@local.test`);
    await sendChatMessage(page, 'Can I afford an emi of 20k');
    await waitForChatResponse(page, 90_000);
    await expect(page.getByText('Affordability Check').first()).toBeVisible({ timeout: 45_000 });

    await sendChatMessage(page, 'but my salary will be credited every month 190000');
    await waitForChatResponse(page, 90_000);

    await expect(page.getByText('Affordability Check').first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Missing amount for income/i)).toHaveCount(0);
    await expect(
      page.getByText(/Yes|within your safe budget|190,?000|20,?000/i).first(),
    ).toBeVisible({ timeout: 30_000 });

    const traces = page.locator('[aria-label="Agent routing trace"]');
    await expect(traces.last()).toContainText(/LLM context|Keyword|compute_affordability/i);
  });

  test('REG-C041: affordability follow-up adjusts target EMI', async ({ page }) => {
    await loginViaUi(page, `chat-afford-emi-${Date.now()}@local.test`);
    await sendChatMessage(page, 'Can I afford an emi of 20k');
    await waitForChatResponse(page, 90_000);
    await expect(page.getByText('Affordability Check').first()).toBeVisible({ timeout: 45_000 });

    await sendChatMessage(page, 'what about 30k emi instead?');
    await waitForChatResponse(page, 90_000);

    await expect(page.getByText('Affordability Check').first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/30,?000|30k/i).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/Missing amount for income/i)).toHaveCount(0);
  });
});
