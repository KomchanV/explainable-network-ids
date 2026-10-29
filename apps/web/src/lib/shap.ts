import type { components } from '@ids/api-client';

type Contribution = Pick<components['schemas']['FeatureContribution'], 'feature' | 'shap_value'>;

export function formatNumber(value: number, signed = false) {
  const magnitude = Math.abs(value);
  const text = magnitude > 0 && magnitude < .000001 ? value.toExponential(2) : value.toFixed(6);
  return signed && value > 0 ? `+${text}` : text;
}

export function waterfall(base: number, features: Contribution[], top = 12) {
  const ordered = [...features].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value));
  const visible = ordered.slice(0, top);
  const rest = ordered.slice(top);
  if (rest.length) visible.push({ feature: `Other features (${rest.length})`, shap_value: rest.reduce((sum, f) => sum + f.shap_value, 0) });
  let running = base;
  return visible.map(feature => {
    const start = running;
    running += feature.shap_value;
    return { ...feature, start, end: running, left: Math.min(start, running), width: Math.abs(feature.shap_value) };
  });
}

/** Invalidation ignores stale results; it does not stop backend computation. */
export function latestRequest() {
  let version = 0;
  return {
    invalidate: () => { version++; },
    async run<T>(work: () => Promise<T>): Promise<{value: T} | undefined> {
      const current = ++version;
      try {
        const value = await work();
        return current === version ? { value } : undefined;
      } catch (cause) {
        if (current === version) throw cause;
        return undefined;
      }
    }
  };
}
