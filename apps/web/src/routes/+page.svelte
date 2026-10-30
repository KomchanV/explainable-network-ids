<script lang="ts">
  import UploadSimpleIcon from 'phosphor-svelte/lib/UploadSimpleIcon';
  import ArrowRightIcon from 'phosphor-svelte/lib/ArrowRightIcon';
  import FileCsvIcon from 'phosphor-svelte/lib/FileCsvIcon';
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
<div class="page-header">
  <div><h1 class="page-title">Analysis overview</h1><p class="page-intro">Review saved traffic predictions, investigate a flow, and understand how the model reached its output.</p></div>
  <a href="/analyze" class="console-button primary">Start traffic analysis</a>
</div>
<div class="space-y-7" aria-busy={loading}>
  {#if loading}
    <section class="panel" role="status"><h2 class="font-semibold">Loading your workspace…</h2><p class="mt-2 text-sm text-muted-foreground">Checking the service and retrieving the current analysis.</p><div aria-hidden="true" class="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">{#each [1, 2, 3, 4] as item (item)}<div class="h-16 rounded bg-muted"></div>{/each}</div></section>
  {:else if current}
    <section aria-labelledby="current-analysis"><div class="mb-5 flex flex-wrap items-center justify-between gap-3"><h2 id="current-analysis" class="text-xl font-semibold">Current analysis</h2><a href={`/analyses/${encodeURIComponent(current.id)}`} class="console-button">Open Flow Explorer</a></div><AnalysisSummary summary={current} /></section>
  {:else}
    <section class="start-surface" aria-labelledby="no-analysis">
      <div class="start-main">
        <FileCsvIcon size={36} weight="light" />
        <h2 id="no-analysis">Start with a saved flow dataset</h2>
        <p>Turn network-flow records into explainable predictions. Import a CIC-IDS2017 CSV, identify predicted DDoS flows, and examine the features behind each result.</p>
        {#if currentError}<p role="alert" class="error-box my-4">{currentError}</p>{/if}
        <a href="/analyze" class="console-button primary"><UploadSimpleIcon size={18} />Import dataset<ArrowRightIcon size={18} /></a>
        <span class="start-format">CSV · Up to 200 MB · 50,000 rows</span>
      </div>
      <div class="start-guide">
        <h3>Your investigation path</h3>
        <ol>
          <li><span>1</span><div><strong>Import & validate</strong><p>Check the dataset against the saved model’s input features.</p></div></li>
          <li><span>2</span><div><strong>Review predictions</strong><p>Filter BENIGN / DDoS outputs and inspect individual flows.</p></div></li>
          <li><span>3</span><div><strong>Understand the evidence</strong><p>Examine SHAP contributions to the model’s P(DDoS) output.</p></div></li>
        </ol>
        <p class="retention-note">Analyses are temporary. This browser remembers one selected analysis; there is no permanent analysis history.</p>
      </div>
    </section>
  {/if}
  <section class="panel service-panel" aria-labelledby="service-heading">
    <div class="flex flex-wrap items-center justify-between gap-3"><h2 id="service-heading" class="text-lg font-semibold">Analysis service</h2><button class="console-button" onclick={refresh} disabled={loading}>{loading ? 'Connecting…' : 'Refresh connection'}</button></div>
    {#if error}<div role="alert" class="error-box mt-4"><h3 class="font-semibold">API connection unavailable</h3><p class="mt-2">{error}</p></div>
    {:else if health}<dl class="mt-5 grid gap-5 text-sm sm:grid-cols-3"><div><dt class="text-muted-foreground">Connection</dt><dd class="mt-2"><span class="badge benign">Connected</span></dd></div><div><dt class="text-muted-foreground">Model status</dt><dd class="mt-2">{health.model_available ? 'Loaded' : 'Unavailable'}</dd></div><div><dt class="text-muted-foreground">API version</dt><dd class="mt-2 font-mono">{health.version}</dd></div></dl>
      {#if !health.model_available}<p class="mt-4 text-sm text-muted-foreground">The operator must configure a trusted model before classification is available.</p>{/if}
    {/if}
    {#if modelError}<p role="alert" class="error-box mt-4">{modelError}</p>{/if}
    {#if model}<details class="mt-5 border-t border-border"><summary class="text-sm font-medium">Saved model and dataset</summary><dl class="mt-3 grid gap-5 text-sm sm:grid-cols-2 lg:grid-cols-4"><div><dt class="text-muted-foreground">Provenance</dt><dd class="mt-2">{model.provenance}</dd></div><div><dt class="text-muted-foreground">Retained features</dt><dd class="mt-2 font-mono">{model.feature_schema.length}</dd></div><div><dt class="text-muted-foreground">Training rows</dt><dd class="mt-2 font-mono">{model.train_rows.toLocaleString()}</dd></div><div><dt class="text-muted-foreground">Held-out rows</dt><dd class="mt-2 font-mono">{model.test_rows.toLocaleString()}</dd></div></dl><p class="mt-4 break-all text-xs text-muted-foreground">Dataset: {model.dataset_filename}</p><a class="console-button mt-4" href="/model-insights">Review saved evaluation</a></details>{/if}
  </section>
</div>
<footer class="mt-8 border-t border-border pt-5 text-xs leading-5 text-muted-foreground">Offline CSV analysis. Predictions are not confirmed security incidents. Prediction rates describe the uploaded data; evaluation accuracy belongs to the saved labeled test set.</footer>

<style>
  .start-surface { display: grid; grid-template-columns: 1.2fr 1fr; border: 1px solid var(--border); border-radius: var(--radius); background: var(--card); overflow: hidden; }
  .start-main { padding: 2.5rem; }
  .start-main :global(> svg) { color: var(--primary); margin-bottom: 1.5rem; }
  .start-main h2 { font-size: 1.5rem; line-height: 1.35; font-weight: 600; letter-spacing: -.02em; max-width: 20ch; }
  .start-main p { margin-block: 1rem 1.75rem; font-size: .875rem; line-height: 1.8; color: var(--muted-foreground); max-width: 54ch; }
  .start-format { display: block; margin-top: 1rem; font-size: .75rem; color: var(--muted-foreground); }
  .start-guide { padding: 2.5rem; background: var(--muted); border-left: 1px solid var(--border); }
  .start-guide h3 { font-size: .875rem; font-weight: 600; margin-bottom: 1.75rem; }
  .start-guide ol { display: grid; gap: 1.5rem; }
  .start-guide li { display: flex; gap: 1rem; font-size: .8rem; }
  .start-guide li > span { display: grid; place-items: center; flex: 0 0 1.75rem; height: 1.75rem; border: 1px solid var(--input); border-radius: 50%; font-variant-numeric: tabular-nums; }
  .start-guide li strong { font-weight: 600; }
  .start-guide li p { margin-top: .3rem; line-height: 1.6; color: var(--muted-foreground); }
  .retention-note { border-top: 1px solid var(--border); padding-top: 1rem; margin-top: 1.75rem; font-size: .75rem; line-height: 1.7; color: var(--muted-foreground); }
  @media (max-width: 1100px) { .start-main, .start-guide { padding: 1.75rem; } }
  @media (max-width: 700px) { .start-surface { grid-template-columns: 1fr; } .start-guide { border-left: 0; border-top: 1px solid var(--border); } }
</style>
