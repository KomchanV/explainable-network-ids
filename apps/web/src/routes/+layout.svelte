<script lang="ts">
  import './layout.css';
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { afterNavigate } from '$app/navigation';
  import ShieldCheckIcon from 'phosphor-svelte/lib/ShieldCheckIcon';
  import SquaresFourIcon from 'phosphor-svelte/lib/SquaresFourIcon';
  import UploadSimpleIcon from 'phosphor-svelte/lib/UploadSimpleIcon';
  import ListMagnifyingGlassIcon from 'phosphor-svelte/lib/ListMagnifyingGlassIcon';
  import ChartBarIcon from 'phosphor-svelte/lib/ChartBarIcon';
  import ListIcon from 'phosphor-svelte/lib/ListIcon';
  import XIcon from 'phosphor-svelte/lib/XIcon';
  import { resolveTheme, themeKey, type ThemePreference } from '#lib/theme.js';
  import type { LayoutProps } from './$types';
  let { children }: LayoutProps = $props();
  let menuOpen = $state(false);
  let ready = $state(false);
  let preference = $state<ThemePreference>('system');
  let systemDark = $state(false);
  const navigation = [
    { href: '/', label: 'Overview', icon: SquaresFourIcon },
    { href: '/analyze', label: 'Import & analyze', icon: UploadSimpleIcon },
    { href: '/explorer', label: 'Traffic Explorer', icon: ListMagnifyingGlassIcon },
    { href: '/model-insights', label: 'Model Insights', icon: ChartBarIcon }
  ];
  const active = (href: string) => href === '/explorer'
    ? page.url.pathname === href || page.url.pathname.startsWith('/analyses/')
    : page.url.pathname === href;
  let section = $derived(navigation.find(item => active(item.href))?.label ?? 'Workspace');
  afterNavigate(() => { menuOpen = false; });
  function applyTheme() {
    document.documentElement.classList.toggle('dark', resolveTheme(preference, systemDark) === 'dark');
  }
  function changeTheme() {
    applyTheme();
    try { localStorage.setItem(themeKey, preference); } catch { /* Theme still works without storage. */ }
  }
  onMount(() => {
    const media = matchMedia('(prefers-color-scheme: dark)');
    systemDark = media.matches;
    try {
      const stored = localStorage.getItem(themeKey);
      if (stored === 'light' || stored === 'dark') preference = stored;
    } catch { /* Use system preference. */ }
    applyTheme();
    ready = true;
    const update = () => { systemDark = media.matches; applyTheme(); };
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  });
</script>

<svelte:head><meta name="description" content="Explainable Network IDS — offline network-flow analysis and model explanations." /></svelte:head>
<a href="#main" class="skip-link">Skip to content</a>
<div class="workspace">
  <aside class="sidebar">
    <div class="sidebar-heading">
      <a href="/" class="brand"><ShieldCheckIcon size={28} weight="duotone" /><span>Explainable IDS<small>Network intelligence</small></span></a>
      <button class="console-button menu-toggle" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="workspace-nav" disabled={!ready} onclick={() => { menuOpen = !menuOpen; }}>
        {#if menuOpen}<XIcon size={20} />{:else}<ListIcon size={20} />{/if}
      </button>
    </div>
    <div id="workspace-nav" class="sidebar-body" class:expanded={menuOpen}>
      <p class="nav-heading">Analysis workspace</p>
      <nav aria-label="Main navigation">
        {#each navigation as item}
          <a href={item.href} aria-current={active(item.href) ? 'page' : undefined}><item.icon size={20} /><span>{item.label}</span></a>
        {/each}
      </nav>
      <div class="sidebar-note"><span class="rail-status">Offline / batch analysis</span><p>Explore saved network flows and understand BENIGN / DDoS predictions.</p></div>
    </div>
  </aside>
  <div class="workspace-body">
    <header class="workspace-header">
      <div class="workspace-location"><span>Workspace</span><span aria-hidden="true">/</span><strong>{section}</strong></div>
      <label class="theme-control">Theme<select disabled={!ready} aria-label="Theme" bind:value={preference} onchange={(event) => { preference = event.currentTarget.value as ThemePreference; changeTheme(); }}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
    </header>
    <main id="main" tabindex="-1">{@render children()}</main>
  </div>
</div>
<style>
  .skip-link { position: fixed; z-index: 100; top: .75rem; left: .75rem; padding: .75rem 1rem; background: var(--card); border: 2px solid var(--ring); transform: translateY(-200%); }
  .skip-link:focus { transform: translateY(0); }
  .workspace { min-height: 100dvh; display: grid; grid-template-columns: 236px minmax(0, 1fr); }
  .sidebar { position: sticky; top: 0; height: 100dvh; overflow-y: auto; border-right: 1px solid var(--border); background: var(--rail); color: var(--rail-text); padding: 1.75rem 1rem; }
  .brand { display: flex; align-items: center; gap: .65rem; font-size: .95rem; font-weight: 650; padding: 0 .5rem; }
  .brand :global(svg) { color: var(--rail-accent); flex-shrink: 0; }
  .brand small { display: block; color: var(--rail-muted); font-size: .68rem; font-weight: 400; margin-top: .35rem; }
  .sidebar-body { display: flex; flex-direction: column; min-height: calc(100% - 4rem); }
  .nav-heading { margin: 2.75rem .9rem .75rem; font-size: .72rem; color: var(--rail-muted); }
  nav { margin-top: 0; display: grid; gap: .5rem; }
  nav a { display: flex; align-items: center; gap: .75rem; padding: .8rem .9rem; border-radius: .5rem; font-size: .875rem; color: var(--rail-muted); }
  nav a:hover { color: var(--rail-text); background: var(--rail-active); }
  nav a[aria-current='page'] { color: var(--rail-text); background: var(--rail-active); font-weight: 600; }
  .sidebar-note { margin-top: auto; padding: 1.5rem .5rem .5rem; color: var(--rail-muted); border-top: 1px solid var(--rail-active); font-size: .75rem; line-height: 1.7; }
  .rail-status { display: block; color: var(--rail-text); font-size: .75rem; font-weight: 600; margin-bottom: .5rem; }
  .workspace-location { display: flex; align-items: center; gap: .75rem; color: var(--muted-foreground); font-size: .8rem; }
  .workspace-location strong { color: var(--foreground); font-weight: 550; }
  .workspace-body { min-width: 0; }
  .workspace-header { min-height: 68px; border-bottom: 1px solid var(--border); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
  .theme-control { display: flex; gap: .65rem; align-items: center; font-size: .75rem; color: var(--muted-foreground); }
  .theme-control select { min-height: 2.75rem; padding: .5rem; border: 1px solid var(--input); border-radius: .5rem; background: var(--card); color: var(--foreground); }
  main { max-width: 1600px; margin-inline: auto; padding: 2rem; outline-offset: -2px; }
  .menu-toggle { display: none; background: var(--rail-active); color: var(--rail-text); border-color: var(--rail-muted); }
  @media (max-width: 900px) {
    .workspace { display: block; }
    .sidebar { position: static; height: auto; padding: 1rem; border-right: 0; border-bottom: 1px solid var(--border); }
    .sidebar-heading { display: flex; justify-content: space-between; align-items: center; gap: .5rem; }
    .sidebar-body { display: none; }
    .sidebar-body.expanded { display: block; }
    .nav-heading { margin-top: 1.25rem; }
    nav { margin-top: .5rem; }
    .sidebar-note { margin: 0; }
    .menu-toggle { display: inline-flex; }
    .workspace-header { min-height: 64px; padding: .75rem 1.25rem; }
    main { padding: 1.5rem 1.25rem; }
  }
</style>
