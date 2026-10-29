import { expect, it } from 'vitest';
import { render } from 'svelte/server';
import LocalShapExplanation from './components/LocalShapExplanation.svelte';
import GlobalShapExplanation from './components/GlobalShapExplanation.svelte';
import type { components } from '@ids/api-client';
import { createApi } from './api.js';

it('renders signed contributions, missing inputs and reconstructed output accessibly', () => {
  const explanation: components['schemas']['LocalExplanation'] = {
    analysis_id: 'sample', row_number: 4, prediction: 'BENIGN', ddos_probability: .2,
    base_value: .5, reconstructed_probability: .2, reconstruction_error: 0,
    class_explained: 'DDoS', model_identifier: 'sha256:fixture', model_provenance: 'synthetic',
    feature_contributions: [
      { feature: 'Long positive feature', raw_value: null, transformed_value: 12, shap_value: .1, absolute_contribution: .1 },
      { feature: 'Negative feature', raw_value: 0, transformed_value: 0, shap_value: -.4, absolute_contribution: .4 },
      { feature: 'Zero feature', raw_value: 1, transformed_value: 1, shap_value: 0, absolute_contribution: 0 }
    ]
  };
  const html = render(LocalShapExplanation, { props: { explanation } }).body;
  expect(html).toContain('SHAP waterfall');
  expect(html).toContain('Missing → fitted median');
  expect(html).toContain('+0.100000');
  expect(html).toContain('-0.400000');
  expect(html).toContain('data-testid="reconstructed-probability"');
  expect(html).toContain('0.200000');
  expect(html).toContain('Long positive feature');
  expect(html).toContain('Zero feature');
  // First occurrences are in chart importance order; table retains model order.
  const table = html.slice(html.indexOf('<table'));
  expect(table.indexOf('Long positive feature')).toBeLessThan(table.indexOf('Negative feature'));
});

it('does not compute global explanations on initial render', () => {
  let calls = 0;
  const api = createApi('http://localhost:8000', async () => { calls++; return Response.json({}); });
  const html = render(GlobalShapExplanation, {props: {analysisId: 'sample', api}}).body;
  expect(calls).toBe(0);
  expect(html).toContain('No global explanation generated');
  expect(html).toContain('Generate Global Explanation');
});
