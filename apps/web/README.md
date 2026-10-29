# Web

SvelteKit 3 / Svelte 5 / TypeScript 6, Tailwind 4, Node adapter, and shadcn-svelte.
Run `pnpm nx serve web` from the repository root. The live dashboard requests
FastAPI health and model metadata through the generated workspace contract.

`components.json`, theme tokens, utility types, and the checked-in Button form
the shadcn foundation. Add future components using the pinned CLI:
`pnpm dlx shadcn-svelte@1.7.1 add <component> --cwd apps/web`.
SvelteKit 3 uses `#lib` aliases and explicit `.js`/`index.js` import paths.

See [development](../../docs/development.md) for configuration and verification.
