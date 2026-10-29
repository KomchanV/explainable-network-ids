import { describe, expect, it } from 'vitest';
import { ApiError, createApi } from './api';

const health = { status: 'ok', version: '0.2.0-alpha.1', model_available: false };

describe('API integration', () => {
  it('requests the configured backend with the supplied fetch implementation', async () => {
    const api = createApi('http://localhost:8000/', async (url) => {
      expect(String(url)).toBe('http://localhost:8000/health');
      return Response.json(health);
    });
    expect(await api.health()).toEqual(health);
  });

  it('preserves structured API errors', async () => {
    const api = createApi('http://localhost:8000', async () => Response.json(
      { error: { code: 'model_unavailable', message: 'Model is unavailable.' } }, { status: 503 }
    ));
    await expect(api.model()).rejects.toMatchObject({
      status: 503, code: 'model_unavailable', message: 'Model is unavailable.'
    });
  });

  it('handles non-JSON proxy errors and connection failures', async () => {
    const api = createApi('http://localhost:8000', async () => new Response('Bad gateway', { status: 502 }));
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
    const offline = createApi('http://localhost:8000', async () => { throw new TypeError('fetch failed'); });
    await expect(offline.health()).rejects.toMatchObject({ code: 'connection_error' });
  });

  it('rejects invalid backend URLs early', () => {
    expect(() => createApi('file:///tmp/model')).toThrow('HTTP');
  });
});
