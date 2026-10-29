<script lang="ts">
  import { createApi } from '#lib/api.js';
  import { latestRequest, formatNumber } from '#lib/shap.js';
  import type { components } from '@ids/api-client';
  import { onDestroy } from 'svelte';
  let { analysisId, api }: { analysisId: string; api: ReturnType<typeof createApi> } = $props();
  let sampleSize = $state(50);
  let result = $state<components['schemas']['GlobalExplanation'] | null>(null);
  let loading = $state(false);
  let error = $state('');
  const request = latestRequest();
  onDestroy(() => request.invalidate());
  async function generate() {
    loading = true; error = ''; result = null;
    try { const response = await request.run(() => api.explainGlobal(analysisId, sampleSize)); if (response) result = response.value; }
    catch (cause) { error = cause instanceof Error ? cause.message : 'Could not generate explanation.'; }
    finally { loading = false; }
  }
</script>
<section aria-label="Global explainability" aria-busy={loading} class="my-8 rounded-lg border border-border bg-card p-6">
  <p class="eyebrow">Global / Uploaded analysis sample</p>
  <h2 class="mt-2 text-xl font-semibold">Global Explainability</h2>
  <p class="my-3 max-w-3xl text-sm text-muted-foreground">Rank features by mean absolute SHAP contribution to P(DDoS) in a deterministic sample of this uploaded analysis. This describes the sampled model outputs, not an entire network or population. It does not show causal effects or contribution direction.</p>
  <form class="my-4 flex flex-wrap items-end gap-4" onsubmit={event => { event.preventDefault(); void generate(); }}>
    <label class="control-label">Sample size (1–100)<input type="number" min="1" max="100" step="1" required bind:value={sampleSize} disabled={loading} /></label>
    <button class="console-button primary" disabled={loading}>{loading ? 'Computing global explanation…' : 'Generate Global Explanation'}</button>
  </form>
  {#if loading}<p role="status" class="text-sm">Computing bounded SHAP sample… This may take a few minutes.</p>{/if}
  {#if error}<p role="alert" class="error-box">{error}</p>{/if}
  {#if result}
    <p class="my-3 text-sm">Sampled flows: <strong data-testid="sample-count">{result.sample_size}</strong> · Seed {result.sampling_seed}</p>
    <p class="text-xs text-muted-foreground">{result.sampling_method}</p>
    <div class="mt-5 overflow-x-auto"><table aria-label="Global feature importance" class="w-full text-left text-sm"><thead><tr><th class="p-3">Rank / Feature</th><th class="p-3">Mean absolute SHAP (probability units)</th></tr></thead><tbody>
      {#each result.feature_importance as feature, index}
        <tr class="border-t border-border"><th scope="row" class="max-w-72 break-words p-3 font-normal">{index + 1}. {feature.feature}</th><td class="p-3"><span class="font-mono">{formatNumber(feature.mean_abs_shap)}</span><div aria-hidden="true" class="mt-2 h-2 bg-muted"><div class="h-2 bg-teal-600" style:width={`${result.feature_importance[0]?.mean_abs_shap ? 100 * feature.mean_abs_shap / result.feature_importance[0].mean_abs_shap : 0}%`}></div></div></td></tr>
      {/each}
    </tbody></table></div>
    <p class="mt-4 break-all text-xs text-muted-foreground">Model {result.model_identifier} · Provenance: {result.model_provenance}</p>
    <p class="mt-2 text-xs text-muted-foreground">Maximum stored-probability reconstruction error: {result.max_reconstruction_error.toExponential(2)}. Uncalibrated probabilities; offline academic prototype.</p>
  {:else if !loading && !error}<p class="text-xs text-muted-foreground">No global explanation generated. Choose a sample size and generate when needed.</p>{/if}
</section>
