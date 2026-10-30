<script lang="ts">
  import UploadSimpleIcon from 'phosphor-svelte/lib/UploadSimpleIcon';
  import { onMount } from 'svelte';
  import { PUBLIC_API_BASE_URL } from '$app/env/public';
  import type { components } from '@ids/api-client';
  import { createApi } from '#lib/api.js';
  import { validateFile } from '#lib/upload.js';
  import AnalysisSummary from '#lib/components/AnalysisSummary.svelte';
  const api = createApi(PUBLIC_API_BASE_URL);
  let file = $state<File | null>(null);
  let busy = $state(false);
  let checking = $state(true);
  let available = $state(false);
  let status = $state('Connecting to API…');
  let error = $state('');
  let features = $state<string[]>([]);
  let schemaError = $state('');
  let summary = $state<components['schemas']['AnalysisSummary'] | null>(null);
  async function check() {
    checking = true; available = false;
    try {
      const health = await api.health(); available = health.model_available;
      if (available) {
        try { features = (await api.model()).feature_schema; schemaError = ''; }
        catch { schemaError = 'Feature list unavailable. Server validation will still check the CSV.'; }
      }
      status = available ? 'API connected · Trusted model available' : 'Model unavailable. Ask the operator to configure a trusted model.';
    } catch (cause) { status = cause instanceof Error ? cause.message : 'API disconnected.'; }
    finally { checking = false; }
  }
  onMount(() => { void check(); });
  function select(selected: File | undefined) {
    if (busy) return;
    summary = null; file = selected ?? null;
    error = file ? validateFile(file) : '';
  }
  async function analyze() {
    if (!file || busy || !available || validateFile(file)) return;
    busy = true; error = ''; summary = null;
    try {
      summary = await api.analyze(file);
      try { localStorage.setItem('ids-current-analysis', summary.id); } catch { /* Storage may be disabled. */ }
    } catch (cause) { error = cause instanceof Error ? cause.message : 'Analysis failed.'; }
    finally { busy = false; }
  }
</script>
<svelte:head><title>Traffic Analysis · Explainable Network IDS</title></svelte:head>
<h1 class="page-title">Import & analyze</h1>
<p class="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">Upload saved network-flow data to classify each row with the existing Random Forest. No live traffic is collected.</p>
<div class="connection-strip my-6" aria-live="polite"><span>{status}</span><button class="console-button" onclick={check} disabled={checking || busy}>Check connection</button></div>
<ol aria-label="Analysis workflow" class="workflow my-7">
  {#each ['Import dataset', 'Validate & run detection', 'Review & investigate'] as step, index}
    <li aria-current={(summary ? index === 2 : file && !error ? index === 1 : index === 0) ? 'step' : undefined}><span>{index + 1}</span>{step}</li>
  {/each}
</ol>

<form onsubmit={(event) => { event.preventDefault(); void analyze(); }} aria-busy={busy} class="upload-form space-y-5">
  <div role="region" aria-label="CSV upload area" class="upload-zone" class:selected={!!file && !error}
    ondragover={(event) => { event.preventDefault(); }}
    ondrop={(event) => { event.preventDefault(); select(event.dataTransfer?.files[0]); }}>
    <UploadSimpleIcon size={32} weight="light" />
    <label for="csv-file" class="block text-lg font-medium">Drop a flow CSV here or choose a file</label>
    <p id="csv-help" class="mt-2 text-sm leading-6 text-muted-foreground">CIC-IDS2017 · UTF-8 / UTF-8-BOM CSV<br />Up to 200 MB and 100,000 rows. Maximum 256 columns and 25.6 million cells.</p>
    <input id="csv-file" type="file" accept=".csv,text/csv" aria-invalid={!!error} aria-describedby={error ? "csv-help csv-error" : "csv-help"} disabled={busy} class="mt-6 block w-full text-sm" onchange={(event) => select(event.currentTarget.files?.[0])} />
    {#if file && !error}<p class="mt-4 text-sm contribution-negative">File checks passed. Ready for server schema validation and detection.</p>{/if}
    {#if file}<p class="mt-5 break-all font-mono text-xs">{file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB</p>{/if}
  </div>
  <button class="console-button primary" type="submit" disabled={!file || !!validateFile(file) || busy || !available}>{busy ? 'Uploading and analyzing…' : 'Analyze CSV'}</button>
  {#if busy}<p role="status" class="text-sm text-muted-foreground">Sending CSV and running batch inference. Larger files may take a few minutes.</p>{/if}
  {#if error}<p id="csv-error" role="alert" class="error-box">{error}</p>{/if}
</form>
<details class="my-5 rounded-lg border border-border bg-card px-5"><summary class="text-sm font-medium">CSV schema requirements{features.length ? ` · ${features.length} model features` : ''}</summary>
  <p class="mb-4 text-sm leading-6 text-muted-foreground">File type and size are checked here. The server validates required columns and numeric values before running inference in the same request. No separate schema-validation endpoint is available.</p>
  {#if schemaError}<p class="mb-4 text-sm text-muted-foreground">{schemaError}</p>{/if}
  {#if features.length}<ul class="mb-5 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">{#each features as feature}<li class="break-words font-mono">{feature}</li>{/each}</ul>{/if}
</details>
<p class="mt-5 text-xs leading-6 text-muted-foreground">Classification uses the loaded Random Forest. Model predictions are not verified incidents. Uploaded analyses expire; export results you need to keep.</p>
{#if summary}
  <div class="mt-10 space-y-6">
    <h2 aria-live="polite" class="text-xl font-semibold">Analysis complete</h2>
    <AnalysisSummary {summary} />
    <p class="text-sm text-muted-foreground">Missing cells processed with saved training medians: {summary.imputed_cells}. Ignored columns: {summary.ignored_columns.join(', ') || 'None'}.</p>
    <a class="console-button primary inline-block" href={`/analyses/${summary.id}`}>Open Flow Explorer</a>
  </div>
{/if}

<style>
  .connection-strip { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 1.25rem; background: var(--card); border: 1px solid var(--border); border-radius: .75rem; font-size: .8rem; }
  .upload-zone { background: var(--card); border: 1px dashed var(--input); border-radius: .75rem; padding: 2.5rem; }
  .upload-zone.selected { border-style: solid; border-color: var(--benign); }
  .upload-zone :global(> svg) { color: var(--primary); margin-bottom: 1.25rem; }
  .upload-zone:focus-within { outline: 2px solid var(--ring); outline-offset: 3px; }
  .upload-zone :global(input[type=file]) { min-height: 2.75rem; }
  .upload-zone :global(input::file-selector-button) { border: 1px solid var(--input); background: var(--muted); color: var(--foreground); padding: .7rem 1rem; border-radius: .375rem; margin-right: 1rem; cursor: pointer; }
  @media (max-width: 640px) { .upload-zone { padding: 1.5rem; } }
  .workflow { display: flex; flex-wrap: wrap; gap: 1rem 2rem; padding-block: 1.25rem; border-block: 1px solid var(--border); }
  .workflow li { display: flex; align-items: center; gap: .65rem; font-size: .8rem; color: var(--muted-foreground); }
  .workflow li span { display: grid; place-items: center; width: 1.75rem; height: 1.75rem; border-radius: 50%; background: var(--muted); font-variant-numeric: tabular-nums; }
  .workflow li[aria-current] { color: var(--foreground); font-weight: 600; }
  .workflow li[aria-current] span { background: var(--primary); color: var(--primary-foreground); }
</style>
