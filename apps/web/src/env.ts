import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
  PUBLIC_API_BASE_URL: {
    public: true,
    schema: (value: string | undefined) => value || 'http://127.0.0.1:8000'
  }
});
