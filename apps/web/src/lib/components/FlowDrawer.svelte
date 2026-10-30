<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import type { Snippet } from 'svelte';
  let { open, onclose, children }: { open: boolean; onclose: () => void; children: Snippet } = $props();
  let dialog: HTMLDialogElement;
  let closeButton: HTMLButtonElement;
  let origin: HTMLElement | null = null;
  let mobile = $state(false);
  let shownModal = false;
  onMount(() => {
    const media = matchMedia('(max-width: 640px)');
    mobile = media.matches;
    const update = () => { mobile = media.matches; };
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  });
  function restoreFocus() {
    if (origin?.isConnected) origin.focus({ preventScroll: true });
    origin = null;
  }
  function close() { onclose(); }
  $effect(() => {
    if (!dialog) return;
    if (open) {
      if (!dialog.open) origin = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      if (!dialog.open || shownModal !== mobile) {
        if (dialog.open) dialog.close();
        if (mobile) dialog.showModal(); else dialog.show();
        shownModal = mobile;
        closeButton.focus({ preventScroll: true });
      }
    } else if (dialog.open) { dialog.close(); restoreFocus(); }
  });
  onDestroy(() => { dialog?.close(); restoreFocus(); });
</script>
<svelte:window onkeydown={(event) => { if (open && event.key === 'Escape' && !event.defaultPrevented) { event.preventDefault(); close(); } }} />
<dialog bind:this={dialog} aria-label="Flow details" oncancel={(event) => { event.preventDefault(); close(); }} class="flow-drawer">
  <div class="drawer-header"><p class="text-sm font-semibold">Flow investigation</p><button bind:this={closeButton} class="console-button" aria-label="Close flow details" onclick={close}>Close</button></div>
  <div class="drawer-content">{@render children()}</div>
</dialog>
<style>
  .flow-drawer { position: fixed; inset: 0 0 0 auto; margin: 0; height: 100dvh; max-height: 100dvh; width: min(720px, 92vw); max-width: 100vw; background: var(--card); color: var(--foreground); border: 0; border-left: 1px solid var(--border); padding: 0; z-index: 50; box-shadow: -12px 0 36px #0003; overflow-y: auto; overscroll-behavior: contain; }
  .drawer-header { position: sticky; top: 0; z-index: 1; display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); background: var(--card); }
  .drawer-content { padding: 1.5rem; overflow-wrap: anywhere; }
  @media (max-width: 640px) { .flow-drawer { width: 100vw; } .drawer-content { padding: 1rem; } }
</style>
