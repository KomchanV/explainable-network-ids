export type ThemePreference = 'system' | 'light' | 'dark';
export const themeKey = 'ids-theme';

export function resolveTheme(preference: string | null, systemDark: boolean): 'light' | 'dark' {
  return preference === 'dark' || (preference !== 'light' && systemDark) ? 'dark' : 'light';
}
