<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  let { analysisId }: { analysisId: string } = $props();
  import { PUBLIC_API_BASE_URL } from '$app/env/public';
  import type { components } from '@ids/api-client';
  import { ApiError, createApi } from '#lib/api.js';
  import FlowDrawer from '#lib/components/FlowDrawer.svelte';
  import AnalysisSummary from '#lib/components/AnalysisSummary.svelte';
  import LocalShapExplanation from '#lib/components/LocalShapExplanation.svelte';
  import GlobalShapExplanation from '#lib/components/GlobalShapExplanation.svelte';
  import { latestRequest } from '#lib/shap.js';
  let explanation = $state<components['schemas']['LocalExplanation'] | null>(null);
  let explaining = $state(false);
  let explanationError = $state('');
  const explanationRequest = latestRequest();
  function resetExplanation() { explanationRequest.invalidate(); explanation = null; explaining = false; explanationError = ''; }
  onDestroy(() => explanationRequest.invalidate());
  async function explain() {
    if (!detail) return;
    const selected = detail.row_number;
    explaining = true; explanationError = '';
    try {
      const response = await explanationRequest.run(() => api.explainFlow(analysisId, selected));
      if (response) { explanation = response.value; explaining = false; }
    } catch (cause) { explanationError = cause instanceof Error ? cause.message : 'Explanation unavailable.'; explaining = false; }
  }
  const api = createApi(PUBLIC_API_BASE_URL);
  let summary = $state<components['schemas']['AnalysisSummary'] | null>(null);
  let result = $state<components['schemas']['FlowPage'] | null>(null);
  let detail = $state<components['schemas']['FlowDetail'] | null>(null);
  let loading = $state(true);
  let detailLoading = $state(false);
  let exporting = $state(false);
  let deleting = $state(false);
  let confirmDelete = $state(false);
  let drawerOpen = $state(false);
  let filterError = $state('');
  let loadVersion = 0;
  let deleted = $state(false);
  let error = $state('');
  let detailError = $state('');
  let actionError = $state('');
  let expired = $state(false);
  let currentPage = $state(1);
  let pageSize = $state(25);
  let prediction = $state('');
  let min = $state(0);
  let max = $state(1);
  let row = $state<number | undefined>(undefined);
  let sort = $state<'row_number' | 'probability'>('row_number');
  let direction = $state<'asc' | 'desc'>('asc');
  let detailVersion = 0;
  function closeDrawer() { drawerOpen = false; resetExplanation(); detailVersion++; detailLoading = false; detail = null; detailError = ''; }
  function clearFilters() { prediction = ''; min = 0; max = 1; row = undefined; sort = 'row_number'; direction = 'asc'; void load(1); }
  async function load(target = 1) {
    filterError = '';
    if (min > max) { filterError = 'Minimum probability must not exceed maximum probability.'; return; }
    const version = ++loadVersion;
    closeDrawer();
    resetExplanation(); loading = true; error = ''; result = null; detail = null; detailLoading = false; expired = false; detailVersion++;
    try {
      const loadedSummary = await api.analysis(analysisId);
      const loadedResult = await api.flows(analysisId, { page: target, page_size: pageSize,
        prediction: prediction === 'BENIGN' || prediction === 'DDoS' ? prediction : undefined,
        probability_min: min, probability_max: max, row_number: row || undefined, sort, direction });
      if (version !== loadVersion) return;
      summary = loadedSummary; result = loadedResult; currentPage = target;
      try { localStorage.setItem('ids-current-analysis', analysisId); } catch { /* Optional browser storage. */ }
    } catch (cause) {
      if (version !== loadVersion) return;
      expired = cause instanceof ApiError && [404, 410].includes(cause.status);
      error = cause instanceof Error ? cause.message : 'Could not load analysis.';
    } finally { if (version === loadVersion) loading = false; }
  }
  async function selectRow(number: number) {
    drawerOpen = true;
    resetExplanation();
    const version = ++detailVersion;
    detailLoading = true; detail = null; detailError = '';
    try { const selected = await api.flow(analysisId, number); if (version === detailVersion) detail = selected; }
    catch (cause) { if (version === detailVersion) detailError = cause instanceof Error ? cause.message : 'Could not load flow.'; }
    finally { if (version === detailVersion) detailLoading = false; }
  }
  async function download() {
    exporting = true; actionError = '';
    try {
      const blob = await api.export(analysisId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'predictions.csv'; anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) { actionError = cause instanceof Error ? cause.message : 'Export failed.'; }
    finally { exporting = false; }
  }
  async function remove() {
    deleting = true; actionError = '';
    try {
      await api.delete(analysisId); closeDrawer(); loadVersion++; deleted = true;
      try { if (localStorage.getItem('ids-current-analysis') === analysisId) localStorage.removeItem('ids-current-analysis'); } catch { /* Optional browser storage. */ }
    } catch (cause) { actionError = cause instanceof Error ? cause.message : 'Deletion failed.'; }
    finally { deleting = false; }
  }
  onMount(() => { void load(); return () => { loadVersion++; detailVersion++; }; });
</script>
<svelte:head><title>Flow Explorer · Explainable Network IDS</title></svelte:head>
<div class="mb-7 flex flex-wrap items-end justify-between gap-4"><div><h1 class="page-title">Flow Explorer</h1><p class="page-intro">Filter saved predictions and inspect the model inputs behind each flow.</p></div><a class="console-button" href="/analyze">New analysis</a></div>
{#if deleted}
  <p role="status">Analysis deleted. Temporary flow data has been removed.</p>
{:else}
  {#if summary}<AnalysisSummary {summary} />{/if}
  {#if error}<div role="alert" class="error-box my-6"><p>{error}</p>{#if expired}<a href="/analyze" class="underline">Upload a CSV again</a>{:else}<button class="console-button mt-3" onclick={() => load(currentPage)}>Retry</button>{/if}</div>{/if}
  {#if !expired}
    <form class="my-7 grid gap-4 rounded-lg border border-border bg-card p-5 sm:grid-cols-3 xl:grid-cols-6" onsubmit={(event) => { event.preventDefault(); void load(1); }}>
      <label class="control-label">Prediction<select bind:value={prediction} disabled={loading}><option value="">All predictions</option><option>BENIGN</option><option>DDoS</option></select></label>
      <label class="control-label">Min P(DDoS)<input type="number" min="0" max="1" step="0.01" required bind:value={min} disabled={loading} /></label>
      <label class="control-label">Max P(DDoS)<input type="number" min="0" max="1" step="0.01" required bind:value={max} disabled={loading} /></label>
      <label class="control-label">Find row number<input type="number" min="1" step="1" bind:value={row} placeholder="All rows" disabled={loading} /></label>
      <label class="control-label">Sort by<select bind:value={sort} disabled={loading}><option value="row_number">Row number</option><option value="probability">P(DDoS)</option></select></label>
      <label class="control-label">Direction<select bind:value={direction} disabled={loading}><option value="asc">Ascending</option><option value="desc">Descending</option></select></label>
      <button class="console-button primary" disabled={loading}>Apply filters</button>
      <button type="button" class="console-button" disabled={loading} onclick={clearFilters}>Clear filters</button>
      <label class="control-label">Rows per page<select bind:value={pageSize} disabled={loading} onchange={(event) => { pageSize = Number(event.currentTarget.value); void load(1); }}><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select></label>
    </form>
    {#if filterError}<p role="alert" class="error-box mb-4">{filterError}</p>{/if}
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3"><p class="text-sm text-muted-foreground">{result ? `${result.total.toLocaleString()} matching flows` : 'Prediction results'}</p><div class="flex flex-wrap gap-3"><button class="console-button" onclick={download} disabled={exporting || !summary}>{exporting ? 'Exporting…' : 'Export all predictions'}</button><button class="console-button" onclick={() => { confirmDelete = true; }} disabled={deleting || !summary}>{deleting ? 'Deleting…' : 'Delete analysis'}</button></div></div>
    {#if confirmDelete}<section aria-label="Confirm analysis deletion" class="panel mb-4"><h2 class="font-semibold">Delete this temporary analysis?</h2><p class="my-3 text-sm text-muted-foreground">Stored flows, predictions and explanations will become unavailable. Export predictions first if needed.</p><div class="flex flex-wrap gap-3"><button class="console-button" onclick={() => { confirmDelete = false; }} disabled={deleting}>Cancel deletion</button><button class="console-button primary" onclick={remove} disabled={deleting}>{deleting ? 'Deleting…' : 'Confirm deletion'}</button></div></section>{/if}
    {#if actionError}<p role="alert" class="error-box mb-4">{actionError}</p>{/if}
    <section aria-label="Flow predictions" aria-busy={loading} class="overflow-x-auto rounded-lg border border-border">
      <table class="w-full text-left text-sm"><caption class="sr-only">Flow predictions. P(DDoS) is an uncalibrated model probability.</caption><thead class="bg-card text-xs text-muted-foreground"><tr><th scope="col" class="p-4">Row number</th><th scope="col" class="p-4">Prediction</th><th scope="col" class="p-4">P(DDoS)</th><th scope="col" class="p-4">Details</th></tr></thead><tbody>
        {#if loading}<tr><td colspan="4" class="p-6"><span role="status">Loading analysis results…</span></td></tr>
        {:else if result && result.items.length}
          {#each result.items as flow (flow.row_number)}<tr class="border-t border-border hover:bg-accent/40"><td class="p-4 font-mono">{flow.row_number}</td><td class="p-4"><span class="badge" class:danger={flow.prediction === 'DDoS'} class:benign={flow.prediction === 'BENIGN'}>{flow.prediction}</span></td><td class="p-4 font-mono">{flow.ddos_probability.toFixed(4)}</td><td class="p-3"><button class="console-button" aria-label={`Inspect row ${flow.row_number}`} onclick={() => selectRow(flow.row_number)}>Inspect</button></td></tr>{/each}
        {:else}<tr><td colspan="4" class="p-6 text-muted-foreground">{error ? 'Results unavailable.' : 'No flows match these filters.'}</td></tr>{/if}
      </tbody></table>
    </section>
    <nav aria-label="Results pagination" class="my-5 flex items-center justify-between gap-4"><button class="console-button" disabled={loading || currentPage <= 1} onclick={() => load(currentPage - 1)}>Previous</button><span class="text-xs">Page {currentPage} of {Math.max(1, Math.ceil((result?.total ?? 0) / pageSize))}</span><button class="console-button" disabled={loading || !result || currentPage * pageSize >= result.total} onclick={() => load(currentPage + 1)}>Next</button></nav>
    <FlowDrawer open={drawerOpen} onclose={closeDrawer}>
    <section aria-label="Selected flow details" aria-live="polite" aria-busy={detailLoading} class="min-w-0">
      <h2 class="text-lg font-semibold">{detail ? `Flow ${detail.row_number} details` : 'Selected flow details'}</h2>
      {#if detailLoading}<p class="mt-3 text-sm">Loading flow…</p>{:else if detailError}<p role="alert" class="error-box mt-3">{detailError}</p>{:else if detail}
        <p class="mt-3 text-sm">Predicted {detail.prediction} · P(DDoS) {detail.ddos_probability.toFixed(4)}</p>
        <p class="mt-2 text-xs text-muted-foreground">Numeric input features before median imputation. Missing or nonfinite cells appear as “Missing”. Ignored metadata is not retained.</p>
        <button class="console-button primary mt-5" onclick={explain} disabled={explaining}>{explaining ? 'Computing explanation…' : 'Explain Prediction'}</button>
        {#if explaining}<p role="status" class="mt-3 text-sm">Computing SHAP for this flow…</p>{/if}
        {#if explanationError}<p role="alert" class="error-box mt-3">{explanationError}</p>{/if}
        {#if explanation}<LocalShapExplanation {explanation} />{/if}
        <dl class="mt-5 grid gap-x-8 gap-y-4 sm:grid-cols-2">{#each Object.entries(detail.features) as [name, value]}<div><dt class="text-xs text-muted-foreground">{name}</dt><dd class="mt-1 break-all font-mono text-sm">{value ?? 'Missing'}</dd></div>{/each}</dl>
      {:else}<p class="mt-3 text-sm text-muted-foreground">Select Inspect on a prediction to view its available model feature values.</p>{/if}
    </section>
    </FlowDrawer>
    <GlobalShapExplanation analysisId={analysisId} {api} />
  {/if}
{/if}
