import type { components, paths } from '@ids/api-client';

type Health = paths['/health']['get']['responses'][200]['content']['application/json'];
type Model = paths['/model']['get']['responses'][200]['content']['application/json'];
type ErrorBody = components['schemas']['ErrorResponse'];

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export function createApi(baseUrl: string, fetcher: typeof fetch = fetch) {
  const base = new URL(baseUrl);
  if (!['http:', 'https:'].includes(base.protocol)) throw new Error('API URL must use HTTP or HTTPS.');
  const prefix = base.href.replace(/\/$/, '');

  async function request<T>(path: string, init: RequestInit = {}, binary = false, timeout = 15000): Promise<T> {
    let response: Response;
    try {
      response = await fetcher(`${prefix}${path}`, { ...init, signal: AbortSignal.timeout(init.method === 'POST' ? 300000 : timeout) });
    } catch {
      if (path.includes('/explanation')) throw new ApiError(0, 'explanation_timeout', 'Explanation request failed or timed out. Retry later; backend computation may still be running.');
      throw new ApiError(0, 'connection_error', 'Cannot reach the API. Check that the backend is running.');
    }
    if (!response.ok) {
      let body: ErrorBody | undefined;
      try { body = await response.json(); } catch { /* A proxy may return HTML. */ }
      throw new ApiError(response.status, body?.error?.code ?? 'http_error',
        body?.error?.message ?? `API request failed (${response.status}).`);
    }
    if (response.status === 204) return undefined as T;
    return (binary ? response.blob() : response.json()) as Promise<T>;
  }

  const analysisPath = (id: string) => `/api/v1/analyses/${encodeURIComponent(id)}`;
  return {
    evaluation: () => request<components['schemas']['ModelEvaluationResponse']>('/model/evaluation'),
    health: () => request<Health>('/health'), model: () => request<Model>('/model'),
    analyze: (file: File) => request<components['schemas']['AnalysisSummary']>(
      `/api/v1/analyses?filename=${encodeURIComponent(file.name)}`,
      { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: file }),
    analysis: (id: string) => request<components['schemas']['AnalysisSummary']>(analysisPath(id)),
    flows: (id: string, query: NonNullable<paths['/api/v1/analyses/{id}/flows']['get']['parameters']['query']> = {}) => {
      const params = new URLSearchParams();
      Object.entries(query).forEach(([key, value]) => { if (value != null) params.set(key, String(value)); });
      return request<components['schemas']['FlowPage']>(`${analysisPath(id)}/flows?${params}`);
    },
    flow: (id: string, row: number) => request<components['schemas']['FlowDetail']>(`${analysisPath(id)}/flows/${row}`),
    explainFlow: (id: string, row: number) => request<components['schemas']['LocalExplanation']>(`${analysisPath(id)}/flows/${row}/explanation`, {}, false, 300000),
    explainGlobal: (id: string, sampleSize = 50) => request<components['schemas']['GlobalExplanation']>(`${analysisPath(id)}/explanations/global?sample_size=${sampleSize}`, {}, false, 300000),
    export: (id: string) => request<Blob>(`${analysisPath(id)}/export`, {}, true),
    delete: (id: string) => request<void>(analysisPath(id), { method: 'DELETE' })
  };
}
