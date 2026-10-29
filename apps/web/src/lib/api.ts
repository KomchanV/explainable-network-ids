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

  async function get<T>(path: string): Promise<T> {
    let response: Response;
    try {
      response = await fetcher(`${prefix}${path}`, { signal: AbortSignal.timeout(5000) });
    } catch {
      throw new ApiError(0, 'connection_error', 'Cannot reach the API. Check that the backend is running.');
    }
    if (!response.ok) {
      let body: ErrorBody | undefined;
      try { body = await response.json(); } catch { /* A proxy may return HTML. */ }
      throw new ApiError(response.status, body?.error?.code ?? 'http_error',
        body?.error?.message ?? `API request failed (${response.status}).`);
    }
    return response.json() as Promise<T>;
  }

  return { health: () => get<Health>('/health'), model: () => get<Model>('/model') };
}
