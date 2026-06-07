import { execSync } from 'child_process';
import path from 'path';
import { SUPER_ADMIN_PASSWORD, SUPER_ADMIN_USERNAME } from './fixtures/data';

/**
 * Bootstrap the super admin before the e2e run (ADR 003 — first admin is
 * created via the one-time script, never self-registration). Idempotent: the
 * script promotes/resets the account if it already exists.
 *
 * Set E2E_SKIP_ADMIN_BOOTSTRAP=1 if the admin is provisioned another way.
 */
export default async function globalSetup(): Promise<void> {
  if (process.env.E2E_SKIP_ADMIN_BOOTSTRAP) return;
  const repoRoot = path.resolve(__dirname, '..');
  const cmd =
    `docker compose run --rm -w /app/apps/api -e PYTHONPATH=/app/apps/api ` +
    `api python -m scripts.create_super_admin ${SUPER_ADMIN_USERNAME} ${SUPER_ADMIN_PASSWORD}`;
  try {
    execSync(cmd, { cwd: repoRoot, stdio: 'inherit' });
  } catch (err) {
    console.warn(
      '[global-setup] Super admin bootstrap failed. Is the docker stack up? ' +
        'You can also run the script manually or set E2E_SKIP_ADMIN_BOOTSTRAP=1.',
      err,
    );
    throw err;
  }
}
