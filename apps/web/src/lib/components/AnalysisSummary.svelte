<script lang="ts">
  import type { components } from '@ids/api-client';
  let { summary, compact = false }: { summary: components['schemas']['AnalysisSummary']; compact?: boolean } = $props();
</script>
<section aria-label="Analysis summary" class="analysis-summary" class:compact>
  {#if compact}
    <div class="summary-strip">
      <div class="dataset-name"><span class="text-xs text-muted-foreground">Current dataset</span><strong class="mt-1 block break-words text-sm font-medium">{summary.dataset_filename}</strong></div>
      <dl class="summary-counts">
        <div><dt>Analyzed flows</dt><dd>{summary.total_flows.toLocaleString()}</dd></div>
        <div><dt>Predicted BENIGN</dt><dd class="contribution-negative">{summary.benign_count.toLocaleString()}</dd></div>
        <div><dt>Predicted DDoS</dt><dd class="contribution-positive">{summary.ddos_count.toLocaleString()}</dd></div>
      </dl>
    </div>
    <details class="summary-disclosure"><summary class="text-xs font-medium">Prediction distribution & dataset details</summary><div class="space-y-4 pb-4">{@render distribution()}{@render provenance()}</div></details>
  {:else}
  <div class="space-y-5">
  <div class="metric-strip">
    {#each [['Analyzed flows', summary.total_flows.toLocaleString()], ['Predicted BENIGN', summary.benign_count.toLocaleString()], ['Predicted DDoS', summary.ddos_count.toLocaleString()], ['Predicted DDoS share', `${summary.ddos_percentage.toFixed(1)}%`]] as [label, value]}
      <div class="metric-cell"><p class="text-xs text-muted-foreground">{label}</p><p class="mt-3 font-mono text-2xl">{value}</p></div>
    {/each}
  </div>
  {@render distribution()}
  {@render provenance()}
  </div>
  {/if}
</section>

{#snippet distribution()}
  <div class="distribution">
    <h3 class="text-sm font-semibold">Prediction distribution</h3>
    <div class="my-4 flex h-3 overflow-hidden rounded bg-muted" aria-hidden="true">
      <div style:width={`${summary.total_flows ? 100 * summary.benign_count / summary.total_flows : 0}%`} style:background="var(--benign)"></div>
      <div style:width={`${summary.total_flows ? 100 * summary.ddos_count / summary.total_flows : 0}%`} style:background="var(--danger)"></div>
    </div>
    <p class="flex flex-wrap gap-4 text-xs"><span class="badge benign">BENIGN · {summary.benign_count.toLocaleString()}</span><span class="badge danger">DDoS · {summary.ddos_count.toLocaleString()}</span></p>
    <p class="mt-3 text-xs text-muted-foreground">Predicted classes for this uploaded dataset, not evaluation accuracy.</p>
  </div>
{/snippet}
{#snippet provenance()}
  {#if !compact}<p class="break-words text-sm font-medium">{summary.dataset_filename}</p>{/if}
  <details><summary class="text-sm font-medium">Dataset and model details</summary>
  <dl class="mt-3 grid gap-3 text-xs text-muted-foreground sm:grid-cols-2">
    <div><dt class="font-medium text-foreground">Model provenance</dt><dd class="mt-1">{summary.model_provenance}</dd></div>
    <div><dt class="font-medium text-foreground">Created / expires</dt><dd class="mt-1">{new Date(summary.created_at).toLocaleString()} / {new Date(summary.expires_at).toLocaleString()}</dd></div>
    <div><dt class="font-medium text-foreground">Model identifier</dt><dd class="mt-1 break-all font-mono">{summary.model_identifier}</dd></div>
  </dl>
  </details>
  <p class="text-xs leading-5 text-muted-foreground">Predictions are not verified ground truth. P(DDoS) is an uncalibrated model output, not confidence or threat severity.</p>
{/snippet}

<style>
  .metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); background: var(--card); border-block: 1px solid var(--border); }
  .metric-cell { padding: 1.25rem; }
  .metric-cell + .metric-cell { border-left: 1px solid var(--border); }
  @media (max-width: 700px) { .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } .metric-cell:nth-child(3) { border-left: 0; } .metric-cell:nth-child(n+3) { border-top: 1px solid var(--border); } }
  .analysis-summary { min-width: 0; }
  .distribution { padding: 1.25rem; border: 1px solid var(--border); border-radius: .75rem; background: var(--card); }
  .summary-strip { display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; padding-block: 1.25rem; border-top: 1px solid var(--border); }
  .dataset-name { min-width: 0; max-width: 32rem; }
  .summary-counts { display: flex; flex-wrap: wrap; gap: 1.5rem; flex-shrink: 0; }
  .summary-counts dt { font-size: .75rem; color: var(--muted-foreground); }
  .summary-counts dd { margin-top: .35rem; font-family: var(--font-mono); font-size: 1rem; }
  .summary-disclosure { border-bottom: 1px solid var(--border); }
  .compact .distribution { border: 0; padding: .25rem 0; background: transparent; }
  @media (max-width: 700px) {
    .summary-strip { flex-direction: column; align-items: flex-start; gap: 1rem; }
    .summary-counts { gap: 1rem; }
  }
</style>
