import { expect, it } from 'vitest';
import { resolveTheme } from './theme';

it('uses system preference unless a valid explicit override is stored', () => {
  expect(resolveTheme(null, true)).toBe('dark');
  expect(resolveTheme('system', false)).toBe('light');
  expect(resolveTheme('light', true)).toBe('light');
  expect(resolveTheme('dark', false)).toBe('dark');
  expect(resolveTheme('invalid', true)).toBe('dark');
});
