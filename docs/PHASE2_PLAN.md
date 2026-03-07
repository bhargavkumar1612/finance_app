# Phase 2 — Ingestion Pipeline — Plan

**Goal:** Unified import pipeline: CSV (one bank first) and PDF → normalizer → deduper → review API. No auto-insert; user confirms before ledger insert. PhonePe CSV as a separate path with intent classification.

**Success criteria:**
- Upload HDFC CSV → parsed → normalized rows → duplicate check → API returns list with `is_duplicate` and confidence; client can POST selected rows to ledger.
- Upload PDF (same bank) → same normalized shape and flow.
- PhonePe CSV → intent (expense/income/transfer/refund/cashback/wallet_load) → normalized → dedupe (UPI txn_id when present).
- All parsers emit the same **normalized transaction** schema; math and amounts never from LLM.

---

## 1. What Exists (Phase 0 / 1)

| Piece | Location | Use in Phase 2 |
|-------|----------|----------------|
| `NormalizedTransaction` | `app/core/schemas.py` | Target schema for every parser output. |
| `Transaction` model, `source` (import \| manual \| ai_extracted) | `app/db/models.py` | Import flow inserts with `source="import"`. |
| `accounts`, `transactions` API | `app/api/` | Confirm flow will POST to `/v1/transactions` (or new bulk endpoint). |
| Stub layout | `app/ingestion/`, `csv_parsers/`, `pdf_parsers/` | Implement here. |

---

## 2. Phase 2 Task Breakdown (Ordered)

| # | Task | Owner | Depends on |
|---|------|--------|------------|
| **2.1** | Normalized contract + staging type | `app/core/schemas.py`, ingestion types | — |
| **2.2** | Normalizer | `app/ingestion/normalizer.py` | 2.1 |
| **2.3** | Deduper (fingerprint + optional store) | `app/ingestion/deduper.py` | 2.1 |
| **2.4** | CSV router + HDFC parser | `app/ingestion/csv_router.py`, `csv_parsers/hdfc.py` | 2.2 |
| **2.5** | Import service (orchestrate parse → normalize → dedupe) | `app/services/import_service.py` | 2.2, 2.3, 2.4 |
| **2.6** | Import API (upload file, return normalized + flags) | `app/api/import_api.py` | 2.5 |
| **2.7** | Confirm/bulk-insert API (accept selected rows → ledger) | `app/api/import_api.py` or transactions | 2.6 |
| **2.8** | PDF pipeline (is_scanned → pdfplumber → table → bank parser) | `app/ingestion/pdf_router.py`, `pdf_parsers/` | 2.2, 2.3 |
| **2.9** | Bank detection (CSV/PDF) | `app/ingestion/bank_detection.py` | — |
| **2.10** | PhonePe parser + intent classifier | `app/ingestion/phonepe/` | 2.2, 2.3 |
| **2.11** | Guided review response (confidence buckets, suggested category) | Optional; `app/core/schemas.py` | 2.6 |

Recommended build order: **2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 2.7** then 2.8, 2.9, 2.10.

---

## 3. File & Module Layout (New/Changed)

```
app/
  core/
    schemas.py              # Add: NormalizedTransactionRow (with is_duplicate, suggested_category)
  ingestion/
    __init__.py
    bank_detection.py       # NEW — detect bank from CSV header / PDF first page
    normalizer.py           # NEW — amount/date/merchant sign, IN number format
    deduper.py              # NEW — fingerprint, check against DB or in-memory set
    csv_router.py           # NEW — dispatch by bank, return list[raw] for normalizer
    pdf_router.py           # NEW — is_scanned, extract_tables, dispatch to pdf_parsers
    csv_parsers/
      __init__.py
      hdfc.py               # NEW — parse HDFC CSV rows
      base.py               # Optional: abstract interface
    pdf_parsers/
      __init__.py
      hdfc_pdf.py           # NEW — parse HDFC PDF table rows
    phonepe/
      __init__.py
      parser.py             # NEW — column mapping
      intent_classifier.py  # NEW — expense/income/transfer/refund/cashback/wallet_load
  services/
    import_service.py       # NEW — parse_file → normalize → dedupe → return rows
  api/
    import_api.py           # NEW — POST /v1/import (upload), POST /v1/import/confirm (bulk insert)
  db/
    (existing; deduper may add import_fingerprints table or use Redis)
```

---

## 4. Data Flow

```
Upload (CSV / PDF / PhonePe CSV)
    ↓
Bank / source detection (header or first page)
    ↓
Parser (bank-specific or PhonePe)
    ↓ raw rows
Normalizer (amount sign, date, IN number format, merchant trim)
    ↓ list[NormalizedTransaction]
Deduper (fingerprint: date|amount|merchant|account_id or UPI txn_id)
    ↓ list[NormalizedTransactionRow] with is_duplicate, fingerprint
Import API returns { "rows": [...], "account_id": "..." }
    ↓
Client shows guided review; user selects rows, maybe edits category
    ↓
POST /v1/import/confirm with selected rows (+ account_id)
    ↓
Ledger insert (source=import), store fingerprint to avoid re-import
```

---

## 5. Key Interfaces

### 5.1 Normalized output (all parsers)

Already in `app/core/schemas.py`: `NormalizedTransaction`: amount, date, merchant, raw_description, reference, confidence.

Add for import API response (optional in 2.1):

```python
class NormalizedTransactionRow(NormalizedTransaction):
    is_duplicate: bool = False
    fingerprint: str | None = None
    suggested_category: str | None = None
```

### 5.2 Normalizer

- **Input:** Raw row (dict or typed row from parser): amount (any format), date (str or date), debit/credit flag, merchant/description.
- **Output:** `NormalizedTransaction` (amount negative for debit, date as date, merchant trimmed, confidence 0–1).
- **Rules:** Indian number format (1,23,456.00 or 123456), DR/CR or parentheses → sign; date parsing (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD).

### 5.3 Deduper

- **Fingerprint:** `hash(f"{date}|{amount}|{normalized_merchant}|{account_id}")` or for PhonePe `hash(f"{upi_txn_id}|{amount}|{date}")` when txn_id present.
- **Storage:** Table `import_fingerprints (user_id, fingerprint, created_at)` or Redis set per user. Check before insert; after confirm-insert, add fingerprints.
- **API:** `check_duplicates(rows: list[NormalizedTransaction], user_id, account_id) -> list[bool]` or in-place `is_duplicate` on each row.

### 5.4 CSV router

- **Input:** File bytes or path, optional `bank_hint: str | None`.
- **Steps:** If bank_hint, use that parser; else detect from first row/header (e.g. column names).
- **Output:** List of raw row dicts (e.g. date, amount, description, debit/credit) for normalizer.

### 5.5 HDFC CSV parser

- **Columns (example):** Date, Narration, Withdrawal, Deposit, Balance (or similar; confirm with real export).
- **Output:** Raw row: `date`, `amount` (positive number), `debit_credit`: "DR"|"CR", `narration`/`description`.
- **Indian format:** Strip commas, parse withdrawal/deposit; withdrawal → negative.

### 5.6 Import service

- **parse_and_normalize(file, filename, bank_hint?, user_id, account_id) -> list[NormalizedTransactionRow]:**
  - Detect type (CSV vs PDF by extension or content).
  - CSV: csv_router → normalizer → deduper (check).
  - PDF: pdf_router → normalizer → deduper.
  - Return rows with is_duplicate and optional suggested_category (rule-based or stub).

### 5.7 Import API

- **POST /v1/import:** `file: Upload`, optional `bank_hint`, optional `account_id`. Response: `{ "rows": list[NormalizedTransactionRow], "account_id": "..." }`.
- **POST /v1/import/confirm:** Body: `{ "account_id", "rows": [ { amount, date, merchant, ... } ] }` (selected rows). Insert into `transactions` (source=import), store fingerprints. Return `{ "inserted": n, "errors": [] }`.

### 5.8 PDF pipeline

- **is_scanned(pdf_path) -> bool:** pdfplumber, first page text length &lt; threshold → scanned.
- **extract_tables(pdf_path) -> list[list]:** pdfplumber extract_tables per page.
- **Bank detection:** First page text / header keywords (HDFC, ICICI, SBI, Axis).
- **HDFC PDF parser:** Map table columns to raw row (date, amount, debit/credit, narration).

### 5.9 PhonePe

- **Parser:** Map columns (Date, Type, From, To, Amount, Status, Notes) to raw row.
- **Intent classifier:** Rules: "Add Money", "Withdrawal" → transfer; "Payment" to merchant → expense; "Received" → income; "Refund", "Cashback" → income; etc.
- **Dedupe:** Prefer UPI txn_id in fingerprint; fallback date+amount+merchant.

---

## 6. Implementation Checklist (Step-by-Step)

### Step 1 — Normalized row + staging (2.1)

- [ ] Add `NormalizedTransactionRow` (or reuse NormalizedTransaction + add `is_duplicate`, `fingerprint`, `suggested_category` in API response model).
- [ ] Document that all parsers must output NormalizedTransaction-compatible dict.

### Step 2 — Normalizer (2.2)

- [ ] `app/ingestion/normalizer.py`: `normalize_row(raw: dict) -> NormalizedTransaction`.
- [ ] Handle: Indian number format, DR/CR/parentheses → sign, date parsing (DD-MM-YYYY, etc.), trim merchant.
- [ ] Unit tests: several raw rows → expected normalized amount/date/merchant.

### Step 3 — Deduper (2.3)

- [ ] Define fingerprint function: `fingerprint(row, account_id) -> str`.
- [ ] Storage: new table `import_fingerprints (id, user_id, account_id, fingerprint, created_at)` or Redis SET per user.
- [ ] `check_duplicates(rows, user_id, account_id) -> list[bool]`; optionally `add_fingerprints(user_id, account_id, fingerprints)` after insert.
- [ ] Unit tests: same row twice → second is_duplicate True.

### Step 4 — CSV router + HDFC parser (2.4)

- [ ] `bank_detection.py`: `detect_bank_from_csv_header(headers: list[str]) -> str | None`.
- [ ] `csv_parsers/hdfc.py`: parse one row (Date, Withdrawal, Deposit, Narration or similar) → raw dict.
- [ ] `csv_router.py`: read CSV (pandas or csv), detect or use bank_hint, call bank parser, return list[raw].
- [ ] Golden file test: sample HDFC CSV (anonymized) in `tests/fixtures/` → expected raw rows.

### Step 5 — Import service (2.5)

- [ ] `services/import_service.py`: `parse_and_normalize(file, filename, user_id, account_id, bank_hint?) -> list[NormalizedTransactionRow]`.
- [ ] Wire csv_router → normalizer → deduper; return rows with is_duplicate.
- [ ] Integration test: upload CSV → service returns normalized list.

### Step 6 — Import API (2.6, 2.7)

- [ ] `api/import_api.py`: POST /v1/import (file upload), call import_service, return `{ rows, account_id }`.
- [ ] POST /v1/import/confirm: body with account_id and list of rows; insert Transaction (source=import), add fingerprints.
- [ ] Integration tests: upload → get rows; confirm → assert transactions in DB.

### Step 7 — PDF pipeline (2.8)

- [ ] `pdf_router.py`: is_scanned, extract_tables, bank_detection from first page text.
- [ ] `pdf_parsers/hdfc_pdf.py`: map table rows to raw dict; normalizer + deduper same as CSV.
- [ ] Wire in import_service when filename is .pdf or content-type PDF.

### Step 8 — PhonePe (2.10)

- [ ] `ingestion/phonepe/parser.py`: column mapping.
- [ ] `ingestion/phonepe/intent_classifier.py`: rules → expense/income/transfer/refund/cashback/wallet_load; set amount sign and category hint.
- [ ] Deduper: UPI txn_id in fingerprint when present.
- [ ] Wire in import_service or separate endpoint for PhonePe CSV.

---

## 7. Testing Strategy (Phase 2)

- **Unit:** Normalizer (many formats), deduper (fingerprint, duplicate check), HDFC CSV parser (golden file), intent classifier (sample rows).
- **Integration:** POST /v1/import with CSV file → 200, response has rows; POST /v1/import/confirm → 200, transactions created and fingerprints stored; re-import same file → rows marked is_duplicate.
- **Fixtures:** `tests/fixtures/sample_hdfc.csv`, optional `sample_hdfc.pdf` (anonymized).

---

## 8. Out of Scope for Phase 2 (Later)

- OCR for scanned PDFs (Phase 2.8 can return “scanned PDF not supported” or stub).
- LLM for category suggestion (use rule-based or fixed “Uncategorized”).
- Multiple banks beyond HDFC (add ICICI/SBI in same pattern).
- Guided review UI (frontend); API only returns rows and confirm endpoint.

---

## 9. Rough Effort (Reference)

| Task | Estimate |
|------|----------|
| 2.1–2.3 Normalizer + Deduper | 1–2 days |
| 2.4 CSV router + HDFC | 1 day |
| 2.5–2.7 Import service + API + confirm | 1 day |
| 2.8 PDF pipeline (one bank) | 1–2 days |
| 2.9 Bank detection | 0.5 day |
| 2.10 PhonePe | 1 day |
| **Total** | **~5–7 days** |

Use this doc as the single source of truth for Phase 2; tick the checkboxes as you implement.
