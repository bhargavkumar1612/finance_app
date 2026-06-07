# 003 — Auth, username login, and super admin

**Status:** accepted

**Context:** The app is multi-user but auth is MVP-only: email-only login auto-creates users; API trusts `X-User-Email` with a `dev@local` fallback. Before any public deployment, the owner wants gated access, password auth, and a super admin who approves signups and password resets manually.

**Decision:**

1. **Username + password** — login identifier is any **unique string** (not required to be a valid email). UI label **Username**. Store as `User.username` (migrate from legacy `email` column).
2. **User status enum:** `pending` | `approved` | `rejected` | `disabled`.
3. **Register flow:** Sign-up form (username + password) → status **`pending`** → user **cannot log in** until super admin approves. No financial data seed until approved (optional: create empty user row only).
4. **Login:** Only **`approved`** users with valid password receive a session token. **`disabled`** and **`pending`** users are blocked with clear error messages.
5. **Rejection cool-off:** Super admin may **reject** a signup. Same username cannot register again for **24 hours** (`rejected_at` + cool-off). Super admin may **instantly override** cool-off and approve.
6. **Forgot password:** User submits a reset request → appears in super admin queue → super admin sets a **new password** and shares it **offline**. No automated email.
7. **Super admin bootstrap:** First super admin created via **one-time setup script / migration** — not self-registration.
8. **Super admin UI:** **Admin** section in the same web app — user count, user list, pending signup queue, password-reset queue.
9. **Super admin powers (v1):**
   - **Approve / reject** signups (with cool-off override)
   - **Disable** user (block login, **keep data**)
   - **Re-enable** disabled user (instant unblock)
   - **Hard delete** user (user + all accounts, transactions, chat, persona, etc.)
   - **Set password** for reset queue items
   - **Not in v1:** impersonation, surgical per-transaction edits
10. **Session:** Long-lived **Bearer token** stored in browser **`localStorage`** (replace today's `finance_user` email-only blob). API validates token on every request; remove `X-User-Email` trust path in production paths.
11. **Password storage:** bcrypt (or argon2) hash only — never log or return plaintext except when super admin sets a temp password (shown once in admin UI for copy/share offline).

**Consequences:**

- Alembic migration: `username`, `password_hash`, `role` (`user` | `super_admin`), `status`, `rejected_at`, session/token table or signed JWT, `password_reset_requests` and/or unified `admin_requests` queue table.
- Replace `apps/api/app/api/auth.py` and `apps/web/lib/AuthContext.tsx` / login page.
- New routes: `/v1/auth/register`, `/v1/auth/login`, `/v1/auth/forgot-password`, `/v1/admin/*` (super admin only).
- New UI: `/register`, `/login` (username + password), `/admin` (super admin only).
- E2E: update `e2e/fixtures/auth.ts` — no more email-only login.
- `LLM_PROVIDER=none` and existing chat/ledger flows must still work after auth swap.
- Phase 5 hardening can add rate limits, audit log, and email later — out of scope for this ADR.

**Decided on:** 2026-06-07 (domain interview Round 9)
