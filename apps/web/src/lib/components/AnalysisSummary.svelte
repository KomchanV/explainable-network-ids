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
  <dl class="grid gap-3 text-xs text-muted-foreground sm:grid-cols-2">
    <div><dt class="font-medium text-foreground">Dataset</dt><dd class="mt-1 break-all">{summary.dataset_filename}</dd></div>
    <div><dt class="font-medium text-foreground">Model provenance</dt><dd class="mt-1">{summary.model_provenance}</dd></div>
    <div><dt class="font-medium text-foreground">Created / expires</dt><dd class="mt-1">{new Date(summary.created_at).toLocaleString()} / {new Date(summary.expires_at).toLocaleString()}</dd></div>
    <div><dt class="font-medium text-foreground">Model identifier</dt><dd class="mt-1 break-all font-mono">{summary.model_identifier}</dd></div>
  </dl>
  <p class="text-xs leading-5 text-muted-foreground">Predictions are not verified ground truth. P(DDoS) is an uncalibrated model output, not confidence or threat severity.</p>
</section>
