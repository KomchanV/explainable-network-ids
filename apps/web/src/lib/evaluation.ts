/** Preserve small error rates without displaying a rounded perfect score. */
export function formatMetric(value: number | null): string {
  if (value === null) return 'Not defined';
  if (value === 0) return '0%';
  if (value === 1) return '100%';
  const percent = value * 100;
  if (percent < .0001) return `${percent.toExponential(4)}%`;
  if (percent > 99.9999) return `100% − ${((1 - value) * 100).toExponential(4)} percentage points`;
  return `${percent.toFixed(6).replace(/\.?0+$/, '')}%`;
}

export const metricDefinitions = [
  ['accuracy', 'Accuracy', 'Share of all held-out flows classified correctly.'],
  ['precision', 'Precision', 'Share of predicted DDoS flows that are actually DDoS.'],
  ['recall', 'Recall', 'Share of actual DDoS flows detected by the model.'],
  ['f1', 'F1 Score', 'Harmonic mean of DDoS precision and recall.'],
  ['false_positive_rate', 'False Positive Rate', 'Share of actual BENIGN flows incorrectly flagged as DDoS. Undefined when no BENIGN flows were evaluated.']
] as const;
