import { describe, expect, it } from 'vitest';
import { formatMetric } from './evaluation';
import { createApi } from './api';

describe('saved evaluation', () => {
  it('preserves boundaries, small errors and undefined FPR', () => {
    expect(formatMetric(null)).toBe('Not defined');
    expect(formatMetric(0)).toBe('0%');
    expect(formatMetric(1)).toBe('100%');
    expect(formatMetric(.99999999)).not.toBe('100%');
    expect(formatMetric(.999999)).toBe('99.9999%');
    expect(formatMetric(1e-10)).toBe('1.0000e-8%');
    expect(formatMetric(.125)).toBe('12.5%');
  });
  it('uses the independent evaluation endpoint', async () => {
    const fetcher = async (url: RequestInfo | URL) => {
      expect(String(url)).toBe('http://localhost:8000/model/evaluation');
      return Response.json({ model: { identifier: 'fixture' } });
    };
    expect((await createApi('http://localhost:8000', fetcher).evaluation()).model.identifier).toBe('fixture');
  });
});
