"""
HDFC Bank CSV parser. Columns vary by export; support common layouts.
Expected columns (case-insensitive): Date, Narration/Description, Withdrawal, Deposit, Balance,
or Value Date, Transaction Date, etc.
"""
import csv
import io
from typing import Any

from app.ingestion.bank_detection import detect_bank_from_csv_headers


def _norm_key(k: str) -> str:
    return k.strip().lower().replace(" ", "_").replace("-", "_")


def _row_to_raw(headers: list[str], row: list[str]) -> dict[str, Any]:
    d: dict[str, Any] = {}
    for i, h in enumerate(headers):
        if i < len(row):
            d[_norm_key(h)] = row[i].strip() if row[i] else ""
    # Map common HDFC names to our raw schema
    raw: dict[str, Any] = {}
    for k, v in d.items():
        if not v:
            continue
        if k in ("date", "transaction_date", "value_date", "txn_date"):
            raw["date"] = raw.get("date") or v
        elif k in ("narration", "description", "particulars", "remarks"):
            raw["narration"] = raw.get("narration") or v
        elif k in ("withdrawal", "withdrawals", "debit", "dr"):
            raw["withdrawal"] = v
        elif k in ("deposit", "deposits", "credit", "cr"):
            raw["deposit"] = v
        elif k in ("balance", "running_balance"):
            raw["balance"] = v
    if "date" not in raw and "value_date" in d:
        raw["date"] = d["value_date"]
    if "date" not in raw and "transaction_date" in d:
        raw["date"] = d["transaction_date"]
    if "narration" not in raw and "description" in d:
        raw["narration"] = d["description"]
    if "narration" not in raw and "particulars" in d:
        raw["narration"] = d["particulars"]
    return raw


def parse_hdfc_csv(content: bytes | str) -> list[dict[str, Any]]:
    """
    Parse HDFC-style CSV. content = file bytes or string.
    Returns list of raw row dicts (date, withdrawal, deposit, narration).
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return []
    headers = [c.strip() for c in rows[0]]
    raw_rows = []
    for row in rows[1:]:
        r = _row_to_raw(headers, row)
        if r.get("date") or r.get("withdrawal") or r.get("deposit"):
            raw_rows.append(r)
    return raw_rows


def parse_csv(content: bytes | str, bank_hint: str | None = None) -> list[dict[str, Any]]:
    """
    Parse CSV: detect bank from header if no hint, then dispatch.
    Returns list of raw row dicts.
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    lines = content.strip().split("\n")
    if not lines:
        return []
    first = lines[0]
    headers = [c.strip() for c in next(csv.reader(io.StringIO(first)))]
    bank = bank_hint or detect_bank_from_csv_headers(headers)
    if bank == "hdfc":
        return parse_hdfc_csv(content)
    # Default: try HDFC-style (Date, Withdrawal, Deposit, Narration)
    return parse_hdfc_csv(content)
