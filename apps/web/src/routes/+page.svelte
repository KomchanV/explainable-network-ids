<script lang="ts">
  import AnalysisSummary from '#lib/components/AnalysisSummary.svelte';
  import { onMount } from 'svelte';
  import { PUBLIC_API_BASE_URL } from '$app/env/public';
  import type { components } from '@ids/api-client';
  import { ApiError, createApi } from '#lib/api.js';
  let current = $state<components['schemas']['AnalysisSummary'] | null>(null);
  let health = $state<components['schemas']['HealthResponse'] | null>(null);
  let model = $state<components['schemas']['ModelResponse'] | null>(null);
  let loading = $state(true);
  let error = $state('');
  let currentError = $state('');
  let modelError = $state('');
  async function refresh() {
    loading = true; error = ''; currentError = ''; modelError = ''; current = null; health = null; model = null;
    const api = createApi(PUBLIC_API_BASE_URL);
    await Promise.all([
      (async () => {
        try {
          health = await api.health();
          if (health.model_available) {
            try { model = await api.model(); }
            catch (cause) { modelError = cause instanceof Error ? cause.message : 'Could not load model metadata.'; }
          }
        } catch (cause) { error = cause instanceof Error ? cause.message : 'Could not connect to the API.'; }
      })(),
      (async () => {
        let id: string | null = null;
        try { id = localStorage.getItem('ids-current-analysis'); } catch { /* Browser storage is optional. */ }
        if (!id) return;
        try { current = await api.analysis(id); }
        catch (cause) {
          currentError = cause instanceof ApiError && [404, 410].includes(cause.status)
            ? 'Your previous analysis has expired or was removed. Import the CSV again to continue.'
            : cause instanceof Error ? cause.message : 'Could not retrieve your current analysis.';
        }
      })()
    ]);
    loading = false;
  }
  onMount(() => { void refresh(); });
</script>
<svelte:head><title>Overview · Explainable Network IDS</title></svelte:head>
<div class="mb-8 flex flex-wrap items-start justify-between gap-4">
  <div><h1 class="page-title">Analysis overview</h1><p class="page-intro">Review saved traffic predictions, investigate a flow, and understand how the model reached its output.</p></div>
  <a href="/analyze" class="console-button primary">Start traffic analysis</a>
</div>
<div class="space-y-7" aria-busy={loading}>
  {#if loading}
    <section class="panel" role="status"><h2 class="font-semibold">Loading your workspace…</h2><p class="mt-2 text-sm text-muted-foreground">Checking the service and retrieving the current analysis.</p><div aria-hidden="true" class="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">{#each [1, 2, 3, 4] as item (item)}<div class="h-16 rounded bg-muted"></div>{/each}</div></section>
  {:else if current}
    <section aria-labelledby="current-analysis"><div class="mb-5 flex flex-wrap items-center justify-between gap-3"><h2 id="current-analysis" class="text-xl font-semibold">Current analysis</h2><a href={`/analyses/${encodeURIComponent(current.id)}`} class="console-button">Open Flow Explorer</a></div><AnalysisSummary summary={current} /></section>
  {:else}
    <section class="panel" aria-labelledby="no-analysis"><h2 id="no-analysis" class="text-xl font-semibold">Start with a saved flow dataset</h2>
      <p class="my-3 max-w-2xl text-sm leading-6 text-muted-foreground">Import a CIC-IDS2017 CSV to get BENIGN / DDoS predictions. Then filter the results and inspect SHAP contributions for individual flows.</p>
      {#if currentError}<p role="alert" class="error-box my-4">{currentError}</p>{/if}
      <ol class="my-6 grid gap-3 text-sm sm:grid-cols-3"><li><strong>1. Import & validate</strong><p class="mt-1 text-muted-foreground">Check file limits and model features.</p></li><li><strong>2. Run detection</strong><p class="mt-1 text-muted-foreground">Classify saved flow records.</p></li><li><strong>3. Investigate & explain</strong><p class="mt-1 text-muted-foreground">Inspect predictions and contributions.</p></li></ol>
      <p class="text-xs text-muted-foreground">Analyses are temporary. This browser remembers one selected analysis; there is no permanent analysis history.</p>
    </section>
  {/if}
  <section class="panel" aria-labelledby="service-heading">
    <div class="flex flex-wrap items-center justify-between gap-3"><h2 id="service-heading" class="text-lg font-semibold">Analysis service</h2><button class="console-button" onclick={refresh} disabled={loading}>{loading ? 'Connecting…' : 'Refresh connection'}</button></div>
    {#if error}<div role="alert" class="error-box mt-4"><h3 class="font-semibold">API connection unavailable</h3><p class="mt-2">{error}</p></div>
    {:else if health}<dl class="mt-5 grid gap-5 text-sm sm:grid-cols-3"><div><dt class="text-muted-foreground">Connection</dt><dd class="mt-2"><span class="badge benign">● Connected</span></dd></div><div><dt class="text-muted-foreground">Model status</dt><dd class="mt-2">{health.model_available ? 'Loaded' : 'Unavailable'}</dd></div><div><dt class="text-muted-foreground">API version</dt><dd class="mt-2 font-mono">{health.version}</dd></div></dl>
      {#if !health.model_available}<p class="mt-4 text-sm text-muted-foreground">The operator must configure a trusted model before classification is available.</p>{/if}
    {/if}
    {#if modelError}<p role="alert" class="error-box mt-4">{modelError}</p>{/if}
    {#if model}<details class="mt-5 border-t border-border"><summary class="text-sm font-medium">Saved model and dataset</summary><dl class="mt-3 grid gap-5 text-sm sm:grid-cols-2 lg:grid-cols-4"><div><dt class="text-muted-foreground">Provenance</dt><dd class="mt-2">{model.provenance}</dd></div><div><dt class="text-muted-foreground">Retained features</dt><dd class="mt-2 font-mono">{model.feature_schema.length}</dd></div><div><dt class="text-muted-foreground">Training rows</dt><dd class="mt-2 font-mono">{model.train_rows.toLocaleString()}</dd></div><div><dt class="text-muted-foreground">Held-out rows</dt><dd class="mt-2 font-mono">{model.test_rows.toLocaleString()}</dd></div></dl><p class="mt-4 break-all text-xs text-muted-foreground">Dataset: {model.dataset_filename}</p><a class="console-button mt-4" href="/model-insights">Review saved evaluation</a></details>{/if}
  </section>
</div>
<footer class="mt-8 border-t border-border pt-5 text-xs leading-5 text-muted-foreground">Offline CSV analysis. Predictions are not confirmed security incidents. Prediction rates describe the uploaded data; evaluation accuracy belongs to the saved labeled test set.</footer>
