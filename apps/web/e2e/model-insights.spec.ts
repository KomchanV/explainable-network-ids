import { expect, test } from '@playwright/test';
import { formatMetric } from '../src/lib/evaluation';

test('dashboard to saved evaluation, matrix and provenance; direct mobile route', async ({ page, request }) => {
  const response = await request.get('http://127.0.0.1:8001/model/evaluation');
  expect(response.ok()).toBeTruthy();
  const snapshot = await response.json();
  await page.goto('/');
  await page.getByRole('link', { name: 'Model Insights', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Saved Held-out Evaluation' })).toBeVisible();
  for (const key of ['accuracy', 'precision', 'recall', 'f1', 'false_positive_rate']) {
    await expect(page.getByTestId(key)).toHaveText(formatMetric(snapshot.evaluation[key]));
  }
  await expect(page.getByRole('columnheader', { name: 'Predicted BENIGN' })).toBeVisible();
  await expect(page.getByRole('rowheader', { name: 'Actual DDoS' })).toBeVisible();
  for (let row = 0; row < 2; row++) for (let col = 0; col < 2; col++) {
    await expect(page.getByTestId(`matrix-${row}-${col}`)).toContainText(snapshot.evaluation.confusion_matrix[row][col].toLocaleString());
  }
  await expect(page.getByText('Synthetic fixture —', { exact: false })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Model Provenance' })).toBeVisible();
  await expect(page.getByText(snapshot.provenance.dataset_sha256)).toBeVisible();
  await expect(page.getByText('SHAP explanations describe model behavior, not causal evidence.')).toBeVisible();
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/model-insights');
  await expect(page.getByTestId('accuracy')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.reload();
  await expect(page.getByTestId('accuracy')).toBeVisible();
});

test('loading, unavailable model, disconnected API and retry', async ({ page }) => {
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/model/evaluation', async route => {
    await gate;
    await route.fulfill({ status: 503, json: { error: { code: 'model_unavailable', message: 'The trusted model is unavailable.' } } });
  });
  await page.goto('/model-insights');
  await expect(page.getByRole('status').filter({ hasText: 'Loading saved evaluation…' })).toHaveText('Loading saved evaluation…');
  release();
  await expect(page.getByRole('alert')).toContainText('The trusted model is unavailable.');
  await page.unroute('**/model/evaluation');
  await page.route('**/model/evaluation', route => route.abort());
  await page.getByRole('button', { name: 'Refresh evaluation' }).click();
  await expect(page.getByRole('alert')).toContainText('Cannot reach the API.');
});

test('missing optional metadata and undefined FPR remain explicit', async ({ page, request }) => {
  const response = await request.get('http://127.0.0.1:8001/model/evaluation');
  const data = await response.json();
  data.provenance.dataset_sha256 = null;
  data.provenance.training_timestamp = null;
  data.methodology.test_fraction = null;
  data.methodology.test_class_counts = null;
  data.evaluation.false_positive_rate = null;
  // UI fixture for absent optional fields; production values always come from the API.
  await page.route('**/model/evaluation', route => route.fulfill({ json: data }));
  await page.goto('/model-insights');
  await expect(page.getByTestId('false_positive_rate')).toHaveText('Not defined');
  await expect(page.getByText('Not recorded', { exact: true })).toHaveCount(4);
});
