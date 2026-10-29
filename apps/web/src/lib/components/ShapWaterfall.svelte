<script lang="ts">
  import type { components } from '@ids/api-client';
  import { waterfall, formatNumber } from '#lib/shap.js';
  let { explanation }: { explanation: components['schemas']['LocalExplanation'] } = $props();
  let top = $state(12);
  let rows = $derived(waterfall(explanation.base_value, explanation.feature_contributions, top));
  // Additive paths may cross 0 or 1: retain those positions instead of clipping.
  let lower = $derived(Math.min(0, ...rows.map(r => r.left)));
  let upper = $derived(Math.max(1, ...rows.map(r => r.left + r.width)));
  const percent = (value: number) => 100 * (value - lower) / (upper - lower);
</script>
<section aria-label="SHAP waterfall" class="mt-6">
  <div class="flex flex-wrap items-center justify-between gap-3"><h3 class="font-semibold">DDoS probability waterfall</h3>
    <label class="control-label">Visible contributions<select bind:value={top}><option value={12}>Top 12 + other features</option><option value={explanation.feature_contributions.length}>All features</option></select></label>
  </div>
  <p class="my-3 text-xs text-muted-foreground">↑ Orange increases P(DDoS) · ↓ Teal decreases P(DDoS). Each bar starts at the previous endpoint. Values use probability units.</p>
  <div class="space-y-2">
    <div class="chart-row"><span>Baseline</span><div class="track"><span class="marker" style:left={`${percent(explanation.base_value)}%`}></span></div><span class="number">{formatNumber(explanation.base_value)}</span></div>
    {#each rows as row}
      <div class="chart-row">
        <span class="break-words">{row.feature}</span>
        <div class="track" aria-hidden="true"><span class:increase={row.shap_value > 0} class:decrease={row.shap_value < 0} class="bar" style:left={`${percent(row.left)}%`} style:width={`${100 * row.width / (upper - lower)}%`}></span><span class="endpoint" style:left={`${percent(row.end)}%`}></span></div>
        <span class="number">{row.shap_value > 0 ? '↑' : row.shap_value < 0 ? '↓' : '—'} {formatNumber(row.shap_value, true)}</span>
      </div>
    {/each}
    <div class="chart-row border-t border-border pt-3"><span>Reconstructed P(DDoS)</span><div class="track"><span class="marker" style:left={`${percent(explanation.reconstructed_probability)}%`}></span></div><span class="number">{formatNumber(explanation.reconstructed_probability)}</span></div>
  </div>
  <p class="mt-3 text-xs text-muted-foreground">Chart domain {formatNumber(lower)} to {formatNumber(upper)}. Full feature values and signed contributions are available in the table below.</p>
</section>
<style>
  .chart-row { display:grid; grid-template-columns:minmax(9rem, 1fr) minmax(7rem, 2fr) minmax(7rem, auto); gap:.75rem; align-items:center; font-size:.75rem; }
  .track { position:relative; height:1.5rem; background:var(--muted); border-inline:1px solid var(--border); }
  .bar { position:absolute; top:.3rem; height:.9rem; }
  .increase { background:#ea580c; } .decrease { background:#0d9488; }
  .marker, .endpoint { position:absolute; height:100%; width:2px; background:var(--foreground); transform:translateX(-1px); }
  .endpoint { height:.35rem; bottom:0; opacity:.65; }
  .number { font-family:monospace; text-align:right; }
  @media(max-width:640px) { .chart-row { grid-template-columns:minmax(0,1fr) auto; } .track { grid-column:1 / -1; grid-row:2; } }
</style>
