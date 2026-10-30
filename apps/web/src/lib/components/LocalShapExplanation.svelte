<script lang="ts">
  import type { components } from '@ids/api-client';
  import ShapWaterfall from './ShapWaterfall.svelte';
  import { formatNumber } from '#lib/shap.js';
  let { explanation }: { explanation: components['schemas']['LocalExplanation'] } = $props();
</script>
<section aria-label="Local SHAP explanation" class="mt-6 border-t border-border pt-6">
  <p class="text-sm text-muted-foreground">Local / Flow {explanation.row_number}</p>
  <h2 class="mt-2 text-xl font-semibold">Why this DDoS probability?</h2>
  <dl class="my-5 grid gap-4 sm:grid-cols-3">
    <div><dt class="control-label">Prediction</dt><dd>{explanation.prediction}</dd></div>
    <div><dt class="control-label">Stored P(DDoS)</dt><dd data-testid="stored-probability" class="font-mono">{formatNumber(explanation.ddos_probability)}</dd></div>
    <div><dt class="control-label">SHAP baseline</dt><dd class="font-mono">{formatNumber(explanation.base_value)}</dd></div>
    <div><dt class="control-label">Reconstructed P(DDoS)</dt><dd data-testid="reconstructed-probability" class="font-mono">{formatNumber(explanation.reconstructed_probability)}</dd></div>
    <div><dt class="control-label">Absolute reconstruction error</dt><dd class="font-mono">{explanation.reconstruction_error.toExponential(2)}</dd></div>
  </dl>
  <p class="text-sm text-muted-foreground">SHAP explains class 1 (DDoS), including flows predicted BENIGN. Baseline + all signed contributions reconstructs the stored probability (absolute tolerance 1e-6, relative tolerance 1e-5). Displayed values are rounded.</p>
  <p class="mt-3 text-sm leading-6 text-muted-foreground">Positive contributions increase the model’s P(DDoS) relative to its baseline; negative contributions decrease it. A large contribution describes model behavior, not proof that a feature caused an attack.</p>
  <ShapWaterfall {explanation} />
  <details class="mt-6"><summary class="cursor-pointer font-semibold">All feature contributions · model feature order</summary>
    <p class="mt-2 text-xs text-muted-foreground">On narrow screens, scroll the table horizontally to review all five columns.</p>
    <!-- Focus is intentional: native arrow-key scrolling exposes off-screen table columns. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div role="region" aria-label="Complete contribution table, horizontally scrollable" tabindex="0" class="mt-3 overflow-x-auto"><table class="w-full text-left text-xs"><thead><tr><th class="p-3">Feature</th><th class="p-3">Available numeric input</th><th class="p-3">Model value after imputation</th><th class="p-3">SHAP contribution</th><th class="p-3">Absolute contribution</th></tr></thead><tbody>
      {#each explanation.feature_contributions as feature}
        <tr class="border-t border-border"><th scope="row" class="max-w-64 break-words p-3 font-normal">{feature.feature}</th><td class="p-3 font-mono">{feature.raw_value === null ? 'Missing → fitted median' : formatNumber(feature.raw_value)}</td><td class="p-3 font-mono">{formatNumber(feature.transformed_value)}</td><td class:contribution-positive={feature.shap_value > 0} class:contribution-negative={feature.shap_value < 0} class="p-3 font-mono">{formatNumber(feature.shap_value, true)}</td><td class="p-3 font-mono">{formatNumber(feature.absolute_contribution)}</td></tr>
      {/each}
    </tbody></table></div>
  </details>
  <p class="mt-5 break-all text-xs text-muted-foreground">Model {explanation.model_identifier} · Provenance: {explanation.model_provenance}</p>
  <p class="mt-3 text-xs text-muted-foreground">These are associations within the model, not causal evidence of an attack. P(DDoS) is uncalibrated and is not validated confidence or severity. Offline academic prototype.</p>
</section>
