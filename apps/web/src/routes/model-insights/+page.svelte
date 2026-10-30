<script lang="ts">
  import CurrentAnalysisExplanation from '#lib/components/CurrentAnalysisExplanation.svelte';
  import { onMount } from 'svelte';
  import { PUBLIC_API_BASE_URL } from '$app/env/public';
  import type { components } from '@ids/api-client';
  import { createApi } from '#lib/api.js';
  import { formatMetric, metricDefinitions } from '#lib/evaluation.js';

  let data = $state<components['schemas']['ModelEvaluationResponse'] | null>(null);
  let loading = $state(true);
  let error = $state('');
  let generation = 0;
  async function refresh() {
    const request = ++generation;
    loading = true; error = ''; data = null;
    try {
      const result = await createApi(PUBLIC_API_BASE_URL).evaluation();
      if (request === generation) data = result;
    } catch (cause) {
      if (request === generation) error = cause instanceof Error ? cause.message : 'Could not retrieve saved evaluation.';
    } finally { if (request === generation) loading = false; }
  }
  onMount(() => { void refresh(); return () => { generation++; }; });
  const missing = (value: unknown) => value == null ? 'Not recorded' : String(value);
</script>

<svelte:head><title>Model Insights · Explainable Network IDS</title></svelte:head>
<div class="page-header">
  <div><h1 class="page-title">Model Insights</h1>
    <p class="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">Saved held-out evaluation of the loaded Random Forest. These results describe labeled test data, independently of any current uploaded analysis.</p></div>
  <button class="console-button" onclick={refresh} disabled={loading}>Refresh evaluation</button>
</div>
<nav class="section-links mt-6" aria-label="Model insight sections"><a href="#uploaded-explanation">Uploaded-data explanations</a><a href="#saved-evaluation">Saved evaluation</a><a href="#provenance">Provenance</a><a href="#limits">Limitations</a></nav>
<div id="uploaded-explanation"><CurrentAnalysisExplanation /></div>
<div id="saved-evaluation" class="mt-8 space-y-8" aria-busy={loading}>
  {#if loading}<p role="status">Loading saved evaluation…</p>
  {:else if error}<div role="alert" class="rounded-lg border border-destructive/40 p-5"><h2 class="font-semibold">Evaluation unavailable</h2><p class="mt-2 text-sm">{error}</p></div>
  {:else if data}
    <section aria-labelledby="overview" class="rounded-lg border border-border bg-card p-6">
      <div class="flex flex-wrap justify-between gap-3"><h2 id="overview" class="text-xl font-semibold">Random Forest · BENIGN / DDoS</h2><span class="text-sm text-primary">Model available</span></div>
      <dl class="mt-5 grid gap-5 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div><dt class="text-muted-foreground">Classifier</dt><dd>{data.model.classifier}</dd></div>
        <div><dt class="text-muted-foreground">Input features</dt><dd>{data.model.feature_count}</dd></div>
        <div><dt class="text-muted-foreground">Artifact format</dt><dd>{data.model.format_version}</dd></div>
        <div class="sm:col-span-2 lg:col-span-3"><dt class="text-muted-foreground">Model artifact identifier</dt><dd class="mt-1 break-all font-mono text-xs">{data.model.identifier}</dd></div>
      </dl>
    </section>
    <section aria-labelledby="metrics"><h2 id="metrics" class="text-xl font-semibold">Saved Held-out Evaluation</h2>
      <p class="mt-2 text-sm text-muted-foreground">{data.evaluation.evaluated_rows.toLocaleString()} evaluated flows. DDoS (1) is the positive class. Precision, recall and F1 use zero when their denominator is zero.</p>
      <dl class="mt-4 grid divide-y divide-border border-y border-border sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-3">
        {#each metricDefinitions as [key, name, definition]}
          <div class="py-5 pr-6"><dt class="text-sm font-medium">{name}</dt><dd class="mt-2 break-words font-mono text-xl tabular-nums" data-testid={key}>{formatMetric(data.evaluation[key])}</dd><dd class="mt-2 text-xs leading-5 text-muted-foreground">{definition}</dd></div>
        {/each}
      </dl>
    </section>
    <section aria-labelledby="matrix"><h2 id="matrix" class="text-xl font-semibold">Confusion Matrix</h2>
      <p class="mt-2 text-sm text-muted-foreground">Rows are actual labels; columns are predicted labels. Saved scikit-learn order: [BENIGN (0), DDoS (1)].</p>
      <!-- svelte-ignore a11y_no_noninteractive_tabindex: keyboard access to a horizontally scrolling data table -->
      <div class="mt-4 table-scroll" role="region" aria-label="Confusion matrix table" tabindex="0"><table class="w-full border-collapse text-left text-sm">
        <caption class="pb-3 text-left text-muted-foreground">Actual counts on the held-out test set</caption>
        <thead><tr><th class="border border-border p-3" scope="col">Actual / Predicted</th><th class="border border-border p-3" scope="col">Predicted BENIGN</th><th class="border border-border p-3" scope="col">Predicted DDoS</th></tr></thead>
        <tbody>{#each ['BENIGN', 'DDoS'] as label, row}<tr><th class="border border-border p-3" scope="row">Actual {label}</th>
          {#each data.evaluation.confusion_matrix[row] as count, col}<td class="border border-border p-4 tabular-nums" class:bg-accent={row === col} data-testid={`matrix-${row}-${col}`}><span class="block text-xs text-muted-foreground">{[['True Negative (TN)', 'False Positive (FP)'], ['False Negative (FN)', 'True Positive (TP)']][row][col]}</span><strong class="mt-1 block font-mono text-xl">{count.toLocaleString()}</strong></td>{/each}
        </tr>{/each}</tbody>
      </table></div>
    </section>
    <section aria-labelledby="provenance" class="rounded-lg border border-border bg-card p-6"><h2 id="provenance" class="text-xl font-semibold">Model Provenance</h2>
      {#if data.provenance.source_type === 'synthetic'}<p class="mt-3 font-medium text-primary">Synthetic fixture — these metrics are test evidence only, not real-world security evidence.</p>
      {:else if data.provenance.source_type === 'cic-ids2017'}<p class="mt-3">CIC-IDS2017 research artifact (saved provenance label).</p>
      {:else}<p class="mt-3">Dataset provenance is unspecified.</p>{/if}
      <p class="mt-3 text-sm leading-6 text-muted-foreground">The provenance label was supplied during model creation; it is not independent proof of dataset authenticity. Missing metadata is shown as “Not recorded”.</p>
      <dl class="mt-5 grid gap-5 text-sm sm:grid-cols-2">
        {#each [
          ['Source type', data.provenance.source_type], ['Dataset filename', data.provenance.dataset_filename],
          ['Training timestamp (UTC)', data.provenance.training_timestamp], ['Training rows', data.methodology.train_rows],
          ['Held-out test rows', data.methodology.test_rows], ['Training rows before subsampling', data.methodology.train_rows_before_subsampling],
          ['Saved test fraction', data.methodology.test_fraction], ['Random seed', data.methodology.random_state],
          ['Label mapping', 'BENIGN = 0; DDoS = 1'],
          ['Training class counts (0 / 1)', data.methodology.train_class_counts ? `${missing(data.methodology.train_class_counts['0'])} / ${missing(data.methodology.train_class_counts['1'])}` : null],
          ['Test class counts (0 / 1)', data.methodology.test_class_counts ? `${missing(data.methodology.test_class_counts['0'])} / ${missing(data.methodology.test_class_counts['1'])}` : null]
        ] as [label, value]}<div><dt class="text-muted-foreground">{label}</dt><dd class="mt-1 break-words">{missing(value)}</dd></div>{/each}
        <div class="sm:col-span-2"><dt class="text-muted-foreground">Saved dataset SHA-256</dt><dd class="mt-1 break-all font-mono text-xs">{missing(data.provenance.dataset_sha256)}</dd></div>
      </dl>
    </section>
    <section aria-labelledby="method"><h2 id="method" class="text-xl font-semibold">Training Methodology</h2><p class="mt-3 text-sm leading-7 text-muted-foreground">{data.methodology.preprocessing_summary}</p><p class="mt-3 text-sm leading-7 text-muted-foreground">{data.methodology.split_method} Evaluation uses labeled held-out data, excluded from fitting. The current implementation defaults to 80/20; the saved test fraction above is authoritative for this artifact.</p></section>
    <section aria-labelledby="limits" class="border-t border-border pt-6"><h2 id="limits" class="text-xl font-semibold">Scientific Limitations</h2><ul class="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-muted-foreground">{#each data.limitations as limitation}<li>{limitation}</li>{/each}</ul></section>
  {/if}
</div>
