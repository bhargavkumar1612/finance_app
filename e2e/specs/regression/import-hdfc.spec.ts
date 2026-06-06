import { test, expect } from '@playwright/test';
import { createBankAccount, loginViaUi, safeClick } from '../../fixtures/helpers';
import { HDFC_SAMPLE_CSV } from '../../fixtures/data';

test.describe('@regression import', () => {
  test('REG-I001 REG-J001: upload HDFC sample CSV and confirm import', async ({ page }) => {
    const suffix = Date.now();
    await loginViaUi(page, `import-${suffix}@local.test`);
    await createBankAccount(page, `Import Test Bank ${suffix}`, 'HDFC');

    await page.goto('/transactions?import=1');
    await expect(page.getByRole('dialog', { name: 'Import bank statement' })).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/Click to upload CSV or PDF/i)).toBeVisible();

    await page.locator('#import-file-input').setInputFiles(HDFC_SAMPLE_CSV);
    const confirmBtn = page.getByRole('button', { name: /Confirm \d+ transactions/ });
    await expect(confirmBtn).toBeVisible({ timeout: 120_000 });
    await safeClick(page, confirmBtn);
    await expect(page.getByText('Import complete!')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/transactions added/i)).toBeVisible();
  });
});
