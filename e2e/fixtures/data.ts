import path from 'path';

export const HDFC_SAMPLE_CSV = path.resolve(__dirname, '../../data/hdfc_12_months_sample.csv');

export function uniqueEmail(prefix = 'e2e'): string {
  return `${prefix}-${Date.now()}@local.test`;
}
