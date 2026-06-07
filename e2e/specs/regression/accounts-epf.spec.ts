import { test, expect } from '@playwright/test';
import { loginViaUi, safeClick } from '../../fixtures/helpers';

test.describe('@regression accounts epf', () => {
  test('REG-F058: create EPF without linked bank shows holdings', async ({ page }) => {
    const suffix = Date.now();
    const epfName = `Acme EPF ${suffix}`;
    await loginViaUi(page, `epf-${suffix}@local.test`);
    await page.goto('/accounts');

    await safeClick(page, page.getByRole('button', { name: 'Add account' }));
    await page.locator('#acc-type').selectOption('epf');
    await expect(page.getByText('Linked bank account')).not.toBeVisible();
    await expect(page.locator('#acc-folio')).toBeVisible();

    await page.locator('#acc-name').fill(epfName);
    await page.locator('#acc-inst').fill('Acme Corp');
    await page.locator('#acc-folio').fill('101234567890');
    await page.locator('#acc-opening-balance').fill('350000');
    await safeClick(page, page.getByRole('button', { name: 'Create account' }));

    await expect(page.getByText(epfName)).toBeVisible();
    await expect(page.getByText(/UAN ••••7890/)).toBeVisible();
    await expect(page.getByText(/Holdings ₹3,50,000/)).toBeVisible();
    await expect(page.locator('#accounts-group-investments')).toContainText(epfName);
  });
});
