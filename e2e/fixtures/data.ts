import path from 'path';

export const HDFC_SAMPLE_CSV = path.resolve(__dirname, '../../data/hdfc_12_months_sample.csv');

export function uniqueEmail(prefix = 'e2e'): string {
  return `${prefix}-${Date.now()}@local.test`;
}

// Auth (Round 9): username + password, super-admin-gated signup.
export function uniqueUsername(prefix = 'e2e'): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
}

export const DEFAULT_PASSWORD = process.env.E2E_USER_PASSWORD ?? 'e2e-user-pass-1';
export const SUPER_ADMIN_USERNAME = process.env.E2E_SUPER_ADMIN_USERNAME ?? 'e2e-admin';
export const SUPER_ADMIN_PASSWORD = process.env.E2E_SUPER_ADMIN_PASSWORD ?? 'e2e-admin-pass-1';
