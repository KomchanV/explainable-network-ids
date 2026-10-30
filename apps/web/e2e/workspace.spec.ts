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

test('flow drawer preserves filters, closes with Escape and restores focus', async ({ page }) => {
  await page.goto('/analyze');
  await expect(page.getByText('API connected · Trusted model available')).toBeVisible();
  await page.getByLabel('Drop a flow CSV').setInputFiles('test-results/flows.csv');
  await page.getByRole('button', { name: 'Analyze CSV', exact: true }).click();
  await page.getByRole('link', { name: 'Open Flow Explorer' }).click();
  await page.getByLabel('Find row number').fill('3');
  await page.getByRole('button', { name: 'Apply filters' }).click();
  const trigger = page.getByRole('button', { name: 'Inspect row 3', exact: true });
  await trigger.click();
  const drawer = page.getByRole('dialog', { name: 'Flow details' });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole('heading', { name: 'Flow 3 details' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Close flow details' })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(drawer).toBeHidden();
  await expect(trigger).toBeFocused();
  await expect(page.getByLabel('Find row number')).toHaveValue('3');
  await expect(page.getByText('1 matching flows')).toBeVisible();
  await page.getByLabel('Min P(DDoS)').fill('0.9');
  await page.getByLabel('Max P(DDoS)').fill('0.1');
  await page.getByRole('button', { name: 'Apply filters' }).click();
  await expect(page.getByRole('alert')).toContainText('Minimum probability must not exceed maximum probability.');
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await expect(page.getByText('40 matching flows')).toBeVisible();
  await page.getByRole('button', { name: 'Delete analysis', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Confirm deletion', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel deletion', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Inspect row 1', exact: true })).toBeVisible();
});

test('overview current analysis, schema guidance, model SHAP and responsive theme captures', async ({ page }) => {
  await page.goto('/analyze');
  await expect(page.getByText('API connected · Trusted model available')).toBeVisible();
  await page.getByText('CSV schema requirements', { exact: false }).click();
  await expect(page.getByText('File type and size are checked here.', { exact: false })).toBeVisible();
  await page.getByLabel('Drop a flow CSV').setInputFiles('test-results/flows.csv');
  await expect(page.getByText('File checks passed.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Analyze CSV', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Analysis complete' })).toBeVisible();
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Current analysis' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Prediction distribution' })).toBeVisible();
  for (const theme of ['light', 'dark']) {
    await page.getByLabel('Theme', { exact: true }).selectOption(theme);
    await page.screenshot({ path: `../../docs/screenshots/v0.3-overview-${theme}.png`, fullPage: true });
  }
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Model Insights', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Uploaded dataset feature importance' })).toBeVisible();
  await page.getByLabel('Sample size (1–100)').fill('9');
  await page.getByRole('button', { name: 'Generate Global Explanation', exact: true }).click();
  await expect(page.getByTestId('sample-count')).toHaveText('9');
  await expect(page.getByRole('heading', { name: 'Saved Held-out Evaluation' })).toBeVisible();
  await page.screenshot({ path: '../../docs/screenshots/v0.3-model-insights-dark.png', fullPage: true });
  await page.getByRole('link', { name: 'Investigate this analysis' }).click();
  await page.getByRole('button', { name: 'Inspect row 1', exact: true }).click();
  await page.getByRole('button', { name: 'Explain Prediction', exact: true }).click();
  await expect(page.getByTestId('stored-probability')).toBeVisible();
  await page.screenshot({ path: '../../docs/screenshots/v0.3-explorer-drawer-dark.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('dialog:modal')).toBeVisible();
  await page.getByRole('button', { name: 'Close flow details' }).focus();
  for (let index = 0; index < 8; index++) {
    await page.keyboard.press('Tab');
    // Native modality may move focus to browser chrome (reported as body), never background controls.
    expect(await page.evaluate(() => document.activeElement === document.body || Boolean(document.activeElement?.closest('dialog')))).toBeTruthy();
  }
  await page.getByRole('dialog', { name: 'Flow details' }).evaluate(el => { el.scrollTop = 0; });
  await page.screenshot({ path: '../../docs/screenshots/v0.3-drawer-mobile-dark.png' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.goto('/analyze');
  await expect(page.getByText('API connected · Trusted model available')).toBeVisible();
  await page.getByLabel('Theme', { exact: true }).selectOption('light');
  await page.screenshot({ path: '../../docs/screenshots/v0.3-import-mobile-light.png', fullPage: true });
  await page.goto('/');
  await page.getByRole('link', { name: 'Open Flow Explorer' }).click();
  await page.getByRole('button', { name: 'Delete analysis', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm deletion', exact: true }).click();
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Start with a saved flow dataset' })).toBeVisible();
  await page.evaluate(() => localStorage.setItem('ids-current-analysis', 'expired-ui-test'));
  await page.goto('/');
  await expect(page.getByRole('alert')).toContainText('Your previous analysis has expired or was removed.');
});

test('theme text and semantic badges meet WCAG AA contrast', async ({ page }) => {
  await page.goto('/');
  for (const theme of ['light', 'dark']) {
    await page.getByLabel('Theme', { exact: true }).selectOption(theme);
    const ratios = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      const luminance = (token: string) => {
        const hex = style.getPropertyValue(token).trim().replace('#', '');
        const rgb = [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16) / 255)
          .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
        return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
      };
      return [
        ['--foreground', '--background'], ['--muted-foreground', '--background'],
        ['--muted-foreground', '--card'], ['--primary-foreground', '--primary'],
        ['--benign', '--benign-surface'], ['--danger', '--danger-surface'],
        ['--accent-foreground', '--accent'], ['--input', '--background'], ['--input', '--card']
      ].map(([text, surface]) => {
        const a = luminance(text), b = luminance(surface);
        return { text, surface, ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05) };
      });
    });
    for (const { text, surface, ratio } of ratios) expect(ratio, `${theme}: ${text} on ${surface}`).toBeGreaterThanOrEqual(text === '--input' ? 3 : 4.5);
  }
});
