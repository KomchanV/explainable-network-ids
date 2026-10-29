<script lang="ts">
  import AnalysisSummary from '#lib/components/AnalysisSummary.svelte';
  import { onMount } from 'svelte';
  import { PUBLIC_API_BASE_URL } from '$app/env/public';
  import type { components } from '@ids/api-client';
  import { ApiError, createApi } from '#lib/api.js';
  import { Button } from '#lib/components/ui/button/index.js';

  let current = $state<components['schemas']['AnalysisSummary'] | null>(null);
  let health = $state<components['schemas']['HealthResponse'] | null>(null);
  let model = $state<components['schemas']['ModelResponse'] | null>(null);
  let loading = $state(true);
  let error = $state('');
  let modelError = $state('');

  async function refresh() {
    loading = true;
    error = '';
    modelError = '';
    health = null;
    model = null;
    try {
      const api = createApi(PUBLIC_API_BASE_URL);
      health = await api.health();
      try {
        const id = localStorage.getItem('ids-current-analysis');
        if (id) current = await api.analysis(id);
      } catch { current = null; }
      if (health.model_available) {
        try { model = await api.model(); }
        catch (cause) { modelError = cause instanceof ApiError ? cause.message : 'Could not load model metadata.'; }
      }
    } catch (cause) {
      error = cause instanceof Error ? cause.message : 'Could not connect to the API.';
    } finally { loading = false; }
  }
  onMount(() => { void refresh(); });
</script>

<svelte:head><title>Dashboard · Explainable Network IDS</title></svelte:head>

<div class="mb-10 flex flex-wrap items-end justify-between gap-5">
  <div>
    <p class="mb-3 font-mono text-xs uppercase tracking-[0.2em] text-primary">01 / Overview</p>
    <h1 class="text-3xl font-semibold tracking-tight sm:text-4xl">Understand the model.<br />Then explore the traffic.</h1>
    <p class="mt-4 max-w-xl text-sm leading-6 text-muted-foreground">A workspace for offline flow classification and model explanations. Start by checking the service and its saved model.</p>
  </div>
  <Button variant="outline" onclick={refresh} disabled={loading}>{loading ? 'Connecting…' : 'Refresh connection'}</Button>
</div>

<div aria-live="polite" aria-busy={loading} class="space-y-5">
  {#if error}
    <div role="alert" class="rounded-lg border border-destructive/40 bg-card p-5">
      <h2 class="font-semibold">API connection unavailable</h2>
      <p class="mt-2 text-sm text-muted-foreground">{error}</p>
    </div>
  {:else if loading}
    <p class="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">Connecting to the analysis service…</p>
  {:else if health}
    <section class="rounded-lg border border-border bg-card p-6" aria-labelledby="service-heading">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 id="service-heading" class="font-semibold">Analysis service</h2>
        <span class="rounded-full bg-accent px-3 py-1 font-mono text-xs text-accent-foreground">● Connected</span>
      </div>
      <dl class="mt-6 grid gap-6 text-sm sm:grid-cols-3">
        <div><dt class="text-muted-foreground">API version</dt><dd class="mt-2 font-mono">{health.version}</dd></div>
        <div><dt class="text-muted-foreground">Model status</dt><dd class="mt-2">{health.model_available ? 'Loaded' : 'Unavailable'}</dd></div>
        <div><dt class="text-muted-foreground">Analysis mode</dt><dd class="mt-2">Offline / batch</dd></div>
      </dl>
    </section>
    {#if modelError}
      <p role="alert" class="rounded-lg border border-destructive/40 p-5 text-sm">{modelError}</p>
    {:else if model}
      <section class="rounded-lg border border-border bg-card p-6" aria-labelledby="model-heading">
        <p class="font-mono text-xs uppercase tracking-widest text-muted-foreground">Saved model</p>
        <h2 id="model-heading" class="mt-2 text-xl font-semibold">Random Forest · BENIGN / DDoS</h2>
        <dl class="mt-6 grid gap-6 text-sm sm:grid-cols-2 xl:grid-cols-4">
          <div><dt class="text-muted-foreground">Provenance</dt><dd class="mt-2 font-mono">{model.provenance}</dd></div>
          <div><dt class="text-muted-foreground">Retained features</dt><dd class="mt-2 font-mono">{model.feature_schema.length}</dd></div>
          <div><dt class="text-muted-foreground">Training rows</dt><dd class="mt-2 font-mono">{model.train_rows.toLocaleString()}</dd></div>
          <div><dt class="text-muted-foreground">Held-out rows</dt><dd class="mt-2 font-mono">{model.test_rows.toLocaleString()}</dd></div>
        </dl>
        <p class="mt-6 break-all border-t border-border pt-4 text-xs text-muted-foreground">Dataset: {model.dataset_filename}</p>
      </section>
    {:else}
      <section class="rounded-lg border border-border bg-card p-6">
        <h2 class="font-semibold">No saved model available</h2>
        <p class="mt-2 text-sm leading-6 text-muted-foreground">The service is running. Classification will be available once the operator configures a trusted model.</p>
      </section>
    {/if}
  {/if}
</div>

<div class="mt-8 space-y-6">
  <a href="/analyze" class="console-button primary inline-block">Start traffic analysis</a>
  {#if current}<h2 class="text-xl font-semibold">Current analysis</h2><AnalysisSummary summary={current} /><a href={`/analyses/${current.id}`} class="console-button inline-block">Open Flow Explorer</a>{/if}
</div>

<footer class="mt-10 border-t border-border pt-5 text-xs leading-5 text-muted-foreground">
  This prototype classifies saved network-flow data. Predictions and explanations describe the fitted model; they do not establish an attack or performance on unseen networks.
</footer>
