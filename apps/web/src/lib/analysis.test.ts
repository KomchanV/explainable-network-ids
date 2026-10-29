import { describe, expect, it } from 'vitest';
import { createApi } from './api.js';
import { validateFile } from './upload.js';

describe('CSV workflow client', () => {
  it('validates CSV selection and limits', () => {
    expect(validateFile({ name: 'x.csv', size: 4 })).toBe('');
    expect(validateFile({ name: 'x.txt', size: 4 })).toMatch(/CSV/);
    expect(validateFile({ name: 'x.csv', size: 0 })).toMatch(/empty/);
    expect(validateFile({ name: 'x.csv', size: 201 * 1024 * 1024 })).toMatch(/200 MB/);
  });
  it('uploads raw CSV and returns actual summary', async () => {
    const summary = { id: 'opaque', total_flows: 2 };
    const api = createApi('http://localhost:8000', async (url, init) => {
      expect(String(url)).toContain('/api/v1/analyses?filename=flows.csv');
      expect(init?.method).toBe('POST');
      expect(new Headers(init?.headers).get('Content-Type')).toBe('text/csv');
      return Response.json(summary, { status: 201 });
    });
    const result = await api.analyze(new File(['x\n1'], 'flows.csv'));
    expect(result).toEqual(summary);
  });
  it('encodes pagination, filtering and details requests', async () => {
    const urls: string[] = [];
    const api = createApi('http://localhost:8000', async (url) => {
      urls.push(String(url)); return Response.json({ items: [], total: 0 });
    });
    await api.flows('opaque', { page: 2, page_size: 50, prediction: 'DDoS', probability_min: 0.4 });
    await api.flow('opaque', 3);
    expect(urls[0]).toContain('page=2&page_size=50&prediction=DDoS&probability_min=0.4');
    expect(urls[1]).toContain('/flows/3');
  });
  it('retains actionable upload errors', async () => {
    const api = createApi('http://localhost:8000', async () => Response.json({ error: {
      code: 'invalid_csv', message: 'Missing required feature columns: Flow Duration'
    } }, { status: 422 }));
    await expect(api.analyze(new File(['x'], 'x.csv'))).rejects.toThrow('Missing required feature');
  });
});
