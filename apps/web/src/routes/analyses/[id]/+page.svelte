<script lang="ts">
  import { page } from '$app/state';
  import FlowExplorer from '#lib/components/FlowExplorer.svelte';
</script>

{#key page.params.id}
  <FlowExplorer analysisId={page.params.id ?? ''} />
{/key}
