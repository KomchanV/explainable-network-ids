import { expect, test } from '@playwright/test';

test('navigation reflects route, theme persists, mobile menu is keyboard operable', async ({ page }) => {
  await page.goto('/');
  const nav = page.getByRole('navigation', { name: 'Main navigation' });
  await expect(nav.locator('[aria-current="page"]')).toHaveText('Overview');
  await nav.getByRole('link', { name: 'Analyses', exact: true }).click();
  await expect(nav.locator('[aria-current="page"]')).toHaveText('Analyses');
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await expect(page.locator('html')).toHaveClass('dark');
  await page.reload();
  await expect(page.locator('html')).toHaveClass('dark');
  await page.getByLabel('Theme', { exact: true }).selectOption('light');
  await expect(page.locator('html')).not.toHaveClass('dark');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(nav).toBeHidden();
  const toggle = page.getByRole('button', { name: 'Open navigation' });
  await toggle.focus();
  await page.keyboard.press('Enter');
  await expect(nav).toBeVisible();
  await nav.getByRole('link', { name: 'Traffic Explorer', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Import a dataset to explore flows' })).toBeVisible();
  await expect(nav).toBeHidden();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
});
