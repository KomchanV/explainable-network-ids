<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  let checking = $state(true);
  onMount(() => {
    let id: string | null = null;
    try { id = localStorage.getItem('ids-current-analysis'); } catch { /* Import remains available. */ }
    if (id) void goto(`/analyses/${encodeURIComponent(id)}`, { replaceState: true });
    else checking = false;
  });
</script>
<svelte:head><title>Traffic Explorer · Explainable Network IDS</title></svelte:head>
<h1 class="page-title">Traffic Explorer</h1>
<p class="page-intro">Investigate individual flow predictions and their feature contributions.</p>
<section class="panel mt-8" aria-live="polite">
  {#if checking}<p role="status">Opening your current analysis…</p>
  {:else}<h2 class="text-lg font-semibold">Import a dataset to explore flows</h2>
    <p class="my-3 max-w-xl text-sm leading-6 text-muted-foreground">Run detection on a saved CSV, then search predictions and inspect individual records here. Analyses are temporary; this browser remembers only your most recently selected analysis.</p>
    <a class="console-button primary mt-3" href="/analyze">Import dataset</a>
  {/if}
</section>
