<script lang="ts">
  import type { components } from '@ids/api-client';
  let { summary }: { summary: components['schemas']['AnalysisSummary'] } = $props();
</script>
<section aria-label="Analysis summary" class="space-y-5">
  <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
    {#each [['Analyzed flows', summary.total_flows.toLocaleString()], ['Predicted BENIGN', summary.benign_count.toLocaleString()], ['Predicted DDoS', summary.ddos_count.toLocaleString()], ['Predicted DDoS share', `${summary.ddos_percentage.toFixed(1)}%`]] as [label, value]}
      <div class="rounded-lg border border-border bg-card p-5"><p class="text-xs text-muted-foreground">{label}</p><p class="mt-3 font-mono text-2xl">{value}</p></div>
    {/each}
  </div>
  <div class="rounded-lg border border-border bg-card p-5">
    <h3 class="text-sm font-semibold">Prediction distribution</h3>
    <div class="my-4 flex h-3 overflow-hidden rounded bg-muted" aria-hidden="true">
      <div style:width={`${summary.total_flows ? 100 * summary.benign_count / summary.total_flows : 0}%`} style:background="var(--benign)"></div>
      <div style:width={`${summary.total_flows ? 100 * summary.ddos_count / summary.total_flows : 0}%`} style:background="var(--danger)"></div>
    </div>
    <p class="flex flex-wrap gap-4 text-xs"><span class="badge benign">BENIGN · {summary.benign_count.toLocaleString()}</span><span class="badge danger">DDoS · {summary.ddos_count.toLocaleString()}</span></p>
    <p class="mt-3 text-xs text-muted-foreground">Predicted classes for this uploaded dataset, not evaluation accuracy.</p>
  </div>
  <p class="break-words text-sm font-medium">{summary.dataset_filename}</p>
  <details><summary class="text-sm font-medium">Dataset and model details</summary>
  <dl class="mt-3 grid gap-3 text-xs text-muted-foreground sm:grid-cols-2">
    <div><dt class="font-medium text-foreground">Model provenance</dt><dd class="mt-1">{summary.model_provenance}</dd></div>
    <div><dt class="font-medium text-foreground">Created / expires</dt><dd class="mt-1">{new Date(summary.created_at).toLocaleString()} / {new Date(summary.expires_at).toLocaleString()}</dd></div>
    <div><dt class="font-medium text-foreground">Model identifier</dt><dd class="mt-1 break-all font-mono">{summary.model_identifier}</dd></div>
  </dl>
  </details>
  <p class="text-xs leading-5 text-muted-foreground">Predictions are not verified ground truth. P(DDoS) is an uncalibrated model output, not confidence or threat severity.</p>
</section>
