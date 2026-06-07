/**
 * @regression Slice 3.2–3.4 E2E tests
 * REG-C031: import_guide card from chat
 * REG-C032: explain_transaction card from chat
 * REG-C033: recategorize_transaction confirm flow
 * REG-C034: create_account_guided SIP confirm flow
 */
import { test, expect } from '@playwright/test';
import { createBankAccount, loginViaUi, safeClick, sendChatMessage, waitForChatReady } from '../../fixtures/helpers';

// ----- REG-C031: import guide card ──────────────────────────────────────────

test.describe('@regression chat slice3 Slice 3.2–3.4', () => {
    test('REG-C031: import guide card in chat', async ({ page }) => {
        const suffix = Date.now();
        await loginViaUi(page, `chat-import-guide-${suffix}@local.test`);
        await sendChatMessage(page, 'import statement');
        await expect(page.getByText('Import statement').first()).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText('Go to Import')).toBeVisible();
    });

    test('REG-C032: explain transaction detail card', async ({ page }) => {
        const suffix = Date.now();
        await loginViaUi(page, `chat-explain-txn-${suffix}@local.test`);
        await sendChatMessage(page, 'explain this charge from Swiggy');
        // card renders (even if no transactions, transaction_detail shows)
        await expect(page.getByText('Transaction detail').first()).toBeVisible({ timeout: 30_000 });
    });

    test('REG-C033: recategorize transaction confirm flow', async ({ page }) => {
        const suffix = Date.now();
        await loginViaUi(page, `chat-recategorize-${suffix}@local.test`);

        // First add an expense so we have something to recategorize
        await sendChatMessage(page, 'add 499 for Netflix');
        await expect(page.getByText('Confirm transaction').first()).toBeVisible({ timeout: 30_000 });
        await safeClick(page, page.getByRole('button', { name: 'Confirm' }).first());
        await expect(page.getByText('Saved').first()).toBeVisible({ timeout: 15_000 });

        await waitForChatReady(page);
        await sendChatMessage(page, 'recategorize Netflix to Entertainment');
        await expect(page.getByText('Confirm transaction').first()).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText(/Entertainment/i).first()).toBeVisible();
    });

    test('REG-C034: create SIP account guided confirm flow', async ({ page }) => {
        const suffix = Date.now();
        await loginViaUi(page, `chat-acct-guided-${suffix}@local.test`);

        // Create a bank account first so the SIP can link to it as parent
        await createBankAccount(page, `HDFC Savings ${suffix}`);

        await page.goto('/chat');
        await waitForChatReady(page);
        await sendChatMessage(page, 'add SIP account 5000 for HDFC Top 200');
        await expect(page.getByText('Confirm new account').first()).toBeVisible({ timeout: 30_000 });
        await expect(page.getByText(/HDFC Top 200/i).first()).toBeVisible();
        await safeClick(page, page.getByRole('button', { name: /create account/i }).first());
        await expect(page.getByText('Account created').first()).toBeVisible({ timeout: 15_000 });
    });
});
