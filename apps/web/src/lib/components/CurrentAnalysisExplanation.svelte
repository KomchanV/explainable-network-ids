<script lang="ts">
  import { onMount } from 'svelte';
  import { PUBLIC_API_BASE_URL } from '$app/env/public';
  import type { components } from '@ids/api-client';
  import { createApi } from '#lib/api.js';
  import GlobalShapExplanation from './GlobalShapExplanation.svelte';
  const api = createApi(PUBLIC_API_BASE_URL);
  let analysis = $state<components['schemas']['AnalysisSummary'] | null>(null);
  let loading = $state(true);
  let error = $state('');
  onMount(() => {
    let active = true;
    void (async () => {
      let id: string | null = null;
      try { id = localStorage.getItem('ids-current-analysis'); } catch { /* Import is still available. */ }
      try { if (id) { const result = await api.analysis(id); if (active) analysis = result; } }
      catch (cause) { if (active) error = cause instanceof Error ? cause.message : 'Analysis unavailable.'; }
      finally { if (active) loading = false; }
    })();
    return () => { active = false; };
  });
</script>
<section aria-labelledby="uploaded-importance" class="mt-7">
  <h2 id="uploaded-importance" class="text-xl font-semibold">Uploaded dataset feature importance</h2>
  <p class="page-intro">Global SHAP here summarizes a sample of your current uploaded dataset. It is separate from the saved held-out evaluation below and is not a training-wide importance measure.</p>
  {#if loading}<p role="status" class="mt-4 text-sm">Looking for a current analysis…</p>
  {:else if error}<p role="alert" class="error-box mt-4">{error} Import a CSV again if the temporary analysis has expired.</p><a class="console-button mt-4" href="/analyze">Import dataset</a>
  {:else if analysis}<p class="mt-4 break-words text-sm">Current dataset: <strong>{analysis.dataset_filename}</strong> · {analysis.total_flows.toLocaleString()} flows</p><a class="mt-2 inline-block text-sm text-primary underline" href={`/analyses/${encodeURIComponent(analysis.id)}`}>Investigate this analysis</a><GlobalShapExplanation analysisId={analysis.id} {api} />
  {:else}<div class="panel mt-5"><p class="text-sm text-muted-foreground">Import a CSV and run detection to generate sampled global SHAP. No current analysis is selected in this browser.</p><a class="console-button mt-4" href="/analyze">Import dataset</a></div>{/if}
</section>
