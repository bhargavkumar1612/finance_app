# Handoff — 2026-06-07 — Auth + Super Admin (Round 9)

## Executive summary

Domain interview **Round 9** is recorded. The app needs real auth before deployment: **username + password**, **super-admin approval** for new signups, **manual password reset** via admin queue, and an **`/admin`** UI. Current code is email-only MVP auth with auto-user creation — must be fully replaced per ADR 003.

## Canonical context

| Source | Key points |
|--------|------------|
| ADR | [docs/decisions/003-auth-super-admin.md](../decisions/003-auth-super-admin.md) |
| Glossary | Username, User status, Super admin, Signup approval queue, Password reset queue, Session token — `docs/DOMAIN_GLOSSARY.md` § Identity and access |
| PROJECT_CONTEXT | [Auth and access (Round 9)](../PROJECT_CONTEXT.md#auth-and-access-round-9--owner-confirmed) |
| Architecture | [AI_PRINCIPLES.md](../AI_PRINCIPLES.md) — keep orchestrator/ledger unchanged; auth is API + UI layer |

## Current code (replace)

| File | Today |
|------|--------|
| `apps/api/app/api/auth.py` | Email-only login; auto-create user; `X-User-Email` header + `dev@local` fallback |
| `apps/api/app/db/models.py` | `User`: `id`, `email`, `created_at` only |
| `apps/web/lib/AuthContext.tsx` | Stores `{id, email}` in `localStorage` |
| `apps/web/app/login/page.tsx` | Email field only |
| `apps/web/lib/api.ts` | `authHeaders` sends `X-User-Email` |
| `e2e/fixtures/auth.ts` | Email-only login helper |

## Recommended implementation slices

### Slice A — Schema + bootstrap

1. Alembic migration:
   - Rename/migrate `email` → `username` (unique, not null)
   - Add `password_hash`, `role` (`user` \| `super_admin`), `status` (`pending` \| `approved` \| `rejected` \| `disabled`), `rejected_at`
   - Add `auth_tokens` table (token hash, user_id, expires_at) **or** signed JWT with secret in env
   - Add `password_reset_requests` (user_id, status, requested_at, resolved_at, resolved_by)
2. Script: `apps/api/scripts/create_super_admin.py` — interactive or env-driven; sets role + approved status
3. Remove `dev@local` auto-create in `get_current_user`

### Slice B — Auth API

| Method | Path | Behavior |
|--------|------|----------|
| POST | `/v1/auth/register` | username + password → `pending`; reject duplicate username; enforce 24h cool-off if `rejected_at` within 24h |
| POST | `/v1/auth/login` | Only `approved` + valid password → bearer token |
| POST | `/v1/auth/forgot-password` | Approved user only → create reset request |
| POST | `/v1/auth/logout` | Invalidate token (if using DB tokens) |
| GET | `/v1/auth/me` | Current user from token |

Errors: clear messages for pending / disabled / wrong password / cool-off.

On **approve** signup: optionally seed default Cash account (today's behavior on first login).

### Slice C — Admin API (super_admin only)

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/v1/admin/stats` | `{ user_count, pending_signups, pending_resets }` |
| GET | `/v1/admin/users` | Paginated list with status, role, created_at |
| GET | `/v1/admin/pending-signups` | `status=pending` |
| POST | `/v1/admin/users/{id}/approve` | → `approved`; seed default account if needed |
| POST | `/v1/admin/users/{id}/reject` | → `rejected`, set `rejected_at=now()` |
| POST | `/v1/admin/users/{id}/disable` | → `disabled` |
| POST | `/v1/admin/users/{id}/enable` | → `approved` |
| DELETE | `/v1/admin/users/{id}` | Hard delete user + cascade all financial data |
| GET | `/v1/admin/password-resets` | Open reset requests |
| POST | `/v1/admin/password-resets/{id}/resolve` | Body: `{ new_password }` — hash, mark resolved, return password once for admin copy |

**Cool-off override:** approve on a `rejected` user within 24h clears cool-off (instant unblock).

Dependency: `require_super_admin` on all `/v1/admin/*`.

### Slice D — Web UI

| Route | Who |
|-------|-----|
| `/register` | Public — username + password; success → "Pending approval" message |
| `/login` | Public — username + password |
| `/login` link | "Forgot password?" → request form (no login) |
| `/admin` | Super admin only — stats, pending signups, password resets, user list with disable/delete |

Update `AuthContext`: store token + user; `authHeaders` → `Authorization: Bearer`.

Redirect: non-admin away from `/admin`; unauthenticated → `/login`.

### Slice E — Tests

**Unit:** password hash, cool-off logic, status gates, admin authorization  
**Integration:** register → pending → approve → login; reject → cool-off → override approve; forgot → admin resolve  
**E2E:** Update `e2e/fixtures/auth.ts`; add REG-A* scenarios (login, register pending, admin approve)  
**Regression:** Existing specs must use approved test user via fixture

## Tests to run before claiming done

```bash
make test-unit
make test-integration
make test-e2e-smoke
# New: pytest apps/api/tests/ -k auth
```

## Out of scope (v1)

- Impersonation
- Automated email
- OAuth
- Admin audit log
- Per-transaction surgical edits

## Assumptions

- bcrypt for passwords; token TTL ~30 days (implementation choice)
- Super admin is exactly one role flag — multiple super admins OK if script creates them
- `LLM_PROVIDER=none` still works after auth swap

## Doc gaps

None — Round 9 recorded in glossary, PROJECT_CONTEXT, ADR 003.
