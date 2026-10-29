import { describe, expect, it } from 'vitest';
import { waterfall, formatNumber, latestRequest } from './shap.js';
import { createApi } from './api.js';

describe('SHAP presentation', () => {
  it('preserves the complete sum when grouping remaining features', () => {
    const rows = waterfall(.4, [
      { feature: 'negative', shap_value: -.1 }, { feature: 'positive', shap_value: .3 },
      { feature: 'zero', shap_value: 0 }, { feature: 'tiny', shap_value: .0000001 }
    ], 2);
    expect(rows.map(r => r.feature)).toEqual(['positive', 'negative', 'Other features (2)']);
    expect(rows[0].start).toBe(.4);
    expect(rows[0].end).toBe(.7);
    expect(rows[1].end).toBeCloseTo(.6);
    expect(rows.at(-1)?.end).toBeCloseTo(.6000001);
    expect(rows[1].left).toBeLessThan(rows[0].end);
    expect(waterfall(.2, [{ feature: 'zero', shap_value: 0 }])[0].width).toBe(0);
  });
  it('formats zero and tiny signed contributions without hiding their signs', () => {
    expect(formatNumber(0, true)).toBe('0.000000');
    expect(formatNumber(.02, true)).toBe('+0.020000');
    expect(formatNumber(-.00000001, true)).toBe('-1.00e-8');
  });
  it('discards responses after a new selection or invalidation', async () => {
    const request = latestRequest();
    let resolve!: (value: number) => void;
    const slow = request.run(() => new Promise<number>(r => { resolve = r; }));
    expect(await request.run(async () => 2)).toEqual({ value: 2 });
    resolve(1);
    expect(await slow).toBeUndefined();
    const invalidated = request.run(async () => 3);
    request.invalidate();
    expect(await invalidated).toBeUndefined();
  });
  it('uses generated-contract explanation endpoints and propagates errors', async () => {
    const urls: string[] = [];
    const api = createApi('http://localhost:8000', async url => {
      urls.push(String(url));
      return Response.json({ analysis_id: 'sample', base_value: .4 });
    });
    expect((await api.explainFlow('a/b', 2)).base_value).toBe(.4);
    await api.explainGlobal('a/b', 30);
    expect(urls[0]).toContain('/a%2Fb/flows/2/explanation');
    expect(urls[1]).toContain('/explanations/global?sample_size=30');
    const busy = createApi('http://localhost:8000', async () => Response.json({error: {code: 'explanation_busy', message: 'Retry later'}}, {status: 503}));
    await expect(busy.explainFlow('x', 1)).rejects.toMatchObject({code: 'explanation_busy'});
  });
});
