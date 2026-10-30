import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';

async function analyze(page: Page) {
  await page.goto('/analyze');
  await expect(page.getByText('API connected · Trusted model available')).toBeVisible();
  await page.getByLabel('Drop a flow CSV').setInputFiles('test-results/flows.csv');
  await page.getByRole('button', { name: 'Analyze CSV', exact: true }).click();
  await page.getByRole('link', { name: 'Open Flow Explorer' }).click();
  await expect(page.getByRole('button', { name: 'Inspect row 1', exact: true })).toBeVisible();
}

test('uploaded flows have real local reconstruction and sampled global importance', async ({ page }) => {
  await analyze(page);
  await expect(page.getByText('No global explanation generated.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Inspect row 1', exact: true }).click();
  const localResponse = page.waitForResponse(r => r.url().endsWith('/flows/1/explanation'));
  await page.getByRole('button', { name: 'Explain Prediction', exact: true }).click();
  const local = await (await localResponse).json();
  const reconstructed = local.base_value + local.feature_contributions.reduce((sum: number, f: {shap_value: number}) => sum + f.shap_value, 0);
  expect(Math.abs(reconstructed - local.ddos_probability)).toBeLessThan(1e-6);
  await expect(page.getByRole('region', { name: 'SHAP waterfall', exact: true })).toBeVisible();
  await expect(page.getByTestId('stored-probability')).toHaveText(local.ddos_probability.toFixed(6));
  await expect(page.getByTestId('reconstructed-probability')).toHaveText(local.reconstructed_probability.toFixed(6));
  await expect(page.getByText('All feature contributions · model feature order')).toBeVisible();
  await page.getByLabel('Visible contributions').selectOption(String(local.feature_contributions.length));
  await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByRole('button', { name: 'Inspect row 2', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Flow 2 details' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Local SHAP explanation', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Explain Prediction', exact: true }).click();
  await expect(page.getByText('SHAP explanation for flow 2', {exact: true})).toBeVisible();
  await page.getByRole('region', {name: 'Local SHAP explanation', exact: true}).screenshot({path: 'test-results/shap-local-desktop.png'});
  await page.setViewportSize({width: 390, height: 844});
  await expect(page.getByRole('region', {name: 'SHAP waterfall', exact: true})).toBeVisible();
  await page.getByRole('region', {name: 'Local SHAP explanation', exact: true}).screenshot({path: 'test-results/shap-local-mobile.png'});
  await page.setViewportSize({width: 1280, height: 720});
  await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByLabel('Sample size (1–100)').fill('9');
  const globalResponse = page.waitForResponse(r => r.url().includes('/explanations/global?'));
  await page.getByRole('button', { name: 'Generate Global Explanation', exact: true }).click();
  const global = await (await globalResponse).json();
  expect(global.sample_size).toBe(9);
  expect(global.sampling_seed).toBe(42);
  await expect(page.getByTestId('sample-count')).toHaveText('9');
  const ranking = page.getByRole('table', {name: 'Global feature importance'});
  await expect(ranking).toContainText(global.feature_importance[0].feature);
  await expect(ranking).toContainText(global.feature_importance[0].mean_abs_shap.toFixed(6));
  await page.getByRole('region', {name: 'Global explainability', exact: true}).screenshot({path: 'test-results/shap-global-desktop.png'});
  if (await page.getByRole('button', { name: 'Close flow details' }).isVisible()) await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByRole('button', {name: 'Delete analysis', exact: true}).click();
  await page.getByRole('button', { name: 'Confirm deletion', exact: true }).click();
});

test('late responses cannot overwrite a newly selected flow', async ({ page }) => {
  await analyze(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  let entered!: () => void;
  const started = new Promise<void>(resolve => { entered = resolve; });
  await page.route('**/flows/1/explanation', async route => {
    const response = await route.fetch();
    entered();
    await gate;
    await route.fulfill({response});
  });
  await page.getByRole('button', { name: 'Inspect row 1', exact: true }).click();
  await page.getByRole('button', { name: 'Explain Prediction', exact: true }).click();
  await expect(page.getByText('Computing SHAP for this flow…')).toBeVisible();
  await started;
  await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByRole('button', { name: 'Inspect row 2', exact: true }).click();
  await page.getByRole('button', { name: 'Explain Prediction', exact: true }).click();
  await expect(page.getByText('SHAP explanation for flow 2', {exact: true})).toBeVisible();
  const lateResponse = page.waitForResponse(r => r.url().endsWith('/flows/1/explanation'));
  release();
  await (await lateResponse).finished();
  await expect(page.getByText('SHAP explanation for flow 1', {exact: true})).toHaveCount(0);
  await expect(page.getByText('SHAP explanation for flow 2', {exact: true})).toBeVisible();
  if (await page.getByRole('button', { name: 'Close flow details' }).isVisible()) await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByRole('button', {name: 'Delete analysis', exact: true}).click();
  await page.getByRole('button', { name: 'Confirm deletion', exact: true }).click();
});

test('failed, expired and model-unavailable explanation requests remain actionable', async ({ page }) => {
  await analyze(page);
  await page.getByRole('button', { name: 'Inspect row 1', exact: true }).click();
  for (const [status, code, message] of [
    [500, 'shap_failure', 'SHAP calculation failed validation. Contact the server operator.'],
    [503, 'model_unavailable', 'The trusted model is unavailable. Contact the server operator.'],
    [410, 'analysis_expired', 'Analysis expired. Upload the CSV again.']
  ] as const) {
    await page.route('**/flows/1/explanation', route => route.fulfill({status, json: {error: {code, message}}}));
    await page.getByRole('button', { name: 'Explain Prediction', exact: true }).click();
    await expect(page.getByRole('alert')).toContainText(message);
    await expect(page.getByRole('region', { name: 'Local SHAP explanation', exact: true })).toHaveCount(0);
  }
  await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.route('**/explanations/global?*', route => route.fulfill({status: 503, json: {error: {code: 'explanation_busy', message: 'Another explanation is being computed. Retry after it finishes.'}}}));
  await page.getByRole('button', { name: 'Generate Global Explanation', exact: true }).click();
  await expect(page.getByRole('region', {name: 'Global explainability', exact: true}).getByRole('alert')).toContainText('Another explanation');
  if (await page.getByRole('button', { name: 'Close flow details' }).isVisible()) await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByRole('button', {name: 'Delete analysis', exact: true}).click();
  await page.getByRole('button', { name: 'Confirm deletion', exact: true }).click();
});


test('client-side navigation between analyses resets selected flow and global explanation', async ({page, request}) => {
  await analyze(page);
  const first = page.url();
  await page.getByRole('button', {name: 'Inspect row 1', exact: true}).click();
  await page.getByRole('button', {name: 'Explain Prediction', exact: true}).click();
  await expect(page.getByText('SHAP explanation for flow 1', {exact: true})).toBeVisible();
  await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByRole('button', {name: 'Generate Global Explanation', exact: true}).click();
  await expect(page.getByRole('table', {name: 'Global feature importance'})).toBeVisible();
  const csv = await readFile('test-results/flows.csv');
  const uploaded = await request.post('http://127.0.0.1:8001/api/v1/analyses?filename=second.csv', {data: csv, headers: {'Content-Type': 'text/csv'}});
  expect(uploaded.status()).toBe(201);
  const second = await uploaded.json();
  await page.evaluate(id => {
    const link = document.createElement('a');
    link.href = `/analyses/${id}`; link.textContent = 'Other analysis'; document.body.append(link);
  }, second.id);
  await page.getByRole('link', {name: 'Other analysis', exact: true}).click();
  await expect(page).toHaveURL(new RegExp(second.id));
  await expect(page.getByText('second.csv', {exact: true})).toBeVisible();
  await expect(page.getByRole('region', {name: 'Local SHAP explanation', exact: true})).toHaveCount(0);
  await expect(page.getByRole('table', {name: 'Global feature importance'})).toHaveCount(0);
  await expect(page.getByText('No global explanation generated.', {exact: false})).toBeVisible();
  if (await page.getByRole('button', { name: 'Close flow details' }).isVisible()) await page.getByRole('button', { name: 'Close flow details' }).click();
  await page.getByRole('button', {name: 'Delete analysis', exact: true}).click();
  await page.getByRole('button', { name: 'Confirm deletion', exact: true }).click();
  await request.delete(`http://127.0.0.1:8001/api/v1/analyses/${first.split('/').at(-1)}`);
});
