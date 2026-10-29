export function validateFile(file: { name: string; size: number }): string {
  if (!file.name.toLowerCase().endsWith('.csv')) return 'Select a CSV file (.csv).';
  if (file.size === 0) return 'The selected file is empty.';
  if (file.size > 200 * 1024 * 1024) return 'CSV exceeds the 200 MB upload limit.';
  return '';
}
