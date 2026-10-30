<script lang="ts">
  import './layout.css';
  import type { LayoutProps } from './$types';
  let { children }: LayoutProps = $props();
  import { page } from '$app/state';
</script>

<svelte:head>
  <meta name="description" content="Explainable Network IDS — offline academic flow classification." />
</svelte:head>

<a href="#main" class="sr-only focus:not-sr-only">Skip to content</a>
<div class="min-h-screen lg:grid lg:grid-cols-[240px_1fr]">
  <aside class="border-b border-border bg-card p-6 lg:border-r lg:border-b-0">
    <a href="/" class="block font-mono text-sm font-semibold tracking-tight">EN / IDS <span class="text-primary">↗</span></a>
    <p class="mt-2 text-xs text-muted-foreground">Explainable network intelligence</p>
    <nav aria-label="Main navigation" class="mt-10 space-y-2">
      <a href="/" aria-current={page.url.pathname === "/" ? "page" : undefined} class="block rounded-md bg-accent px-3 py-2 text-sm font-medium">Dashboard</a>
      <a href="/analyze" class="block px-3 py-2 text-sm">Traffic Analysis</a>
      <a href="/model-insights" aria-current={page.url.pathname === '/model-insights' ? 'page' : undefined} class="block px-3 py-2 text-sm">Model Insights</a>
    </nav>
    <p class="mt-12 max-w-48 text-xs leading-relaxed text-muted-foreground">Offline academic prototype.<br />BENIGN / DDoS classification.</p>
  </aside>
  <div>
    <header class="flex items-center justify-between border-b border-border px-6 py-4 lg:px-10">
      <span class="text-xs uppercase tracking-[0.16em] text-muted-foreground">Research workspace</span>
      <span class="font-mono text-xs">v0.2.0-alpha.1</span>
    </header>
    <main id="main" class="mx-auto max-w-6xl px-6 py-10 lg:px-10 lg:py-14">{@render children()}</main>
  </div>
</div>
