"""
HDFC PDF statement: extract table rows into raw row dicts (date, withdrawal, deposit, narration).
Supports both savings/current (Withdrawal/Deposit) and loan statements (Date, Particulars, Debit/Credit).
"""
import re
from typing import Any

# Loan statement: "Debit/Credit" or "Debit / Credit" column has values like "209,369.00 DR", "10,290.00 CR"
_AMOUNT_DR_CR = re.compile(r"([\d,]+(?:\.\d{2})?)\s*(DR|CR)\s*$", re.IGNORECASE)


def _cell(row: list, i: int) -> str:
    if i < len(row) and row[i] is not None:
        return str(row[i]).strip()
    return ""


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", h.strip().lower())


def _find_column_indices(headers: list[str]) -> dict[str, int]:
    """Return column index for date, particulars, debit_credit (combined DR/CR column)."""
    out: dict[str, int] = {}
    for i, h in enumerate(headers):
        n = _norm_header(h)
        if "date" in n and "value" not in n and "date" not in out:
            out["date"] = i
        elif "particular" in n or "narration" in n or "description" in n:
            out["particulars"] = i
        elif "debit" in n and "credit" in n:
            out["debit_credit"] = i
        elif "withdrawal" in n or "debit" in n:
            out["debit"] = i
        elif "deposit" in n or "credit" in n:
            out["credit"] = i
    return out


def _parse_amount_dr_cr(cell: str) -> tuple[str | None, str | None]:
    """
    Parse cell like "209,369.00 DR" or "10,290.00 CR". Returns (amount_str, "DR"|"CR").
    """
    if not cell:
        return None, None
    m = _AMOUNT_DR_CR.search(cell.strip())
    if m:
        amt = m.group(1).replace(",", "")
        dc = m.group(2).upper()
        return amt, dc
    return None, None


def _looks_like_date(s: str) -> bool:
    if not s or len(s) < 6:
        return False
    s = s.replace(",", "").replace(" ", "")
    parts = s.replace("-", "/").split("/")
    if len(parts) != 3:
        return False
    try:
        a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
        return (1 <= a <= 31 and 1 <= b <= 12) or (1 <= b <= 31 and 1 <= a <= 12) or (1900 <= a <= 2100)
    except ValueError:
        return False


def _is_likely_currency_amount(s: str) -> bool:
    """True if string looks like a currency amount (has decimal or reasonable length), not a 10-digit ref no."""
    if not s:
        return False
    t = s.replace(",", "").replace(" ", "").lstrip("(").rstrip(")")
    if "." in t:
        return True
    # Cheque/reference numbers are often 10+ digits; amounts are usually smaller
    if t.replace(".", "").replace("-", "").isdigit():
        return len(t.replace(".", "").replace("-", "")) <= 9
    return False


def _first_currency_like(cells: list[str]) -> str | None:
    """First cell that looks like currency (not a long integer like cheque number)."""
    for c in cells:
        if not c:
            continue
        if _parse_amount_dr_cr(c)[0]:
            return c
        if _is_likely_currency_amount(c):
            return c
    return None


def tables_to_raw_rows(tables: list[list[list[str | None]]]) -> list[dict[str, Any]]:
    """
    Convert extracted tables to raw row dicts.
    - If a header row looks like "Date", "Particulars", "Debit/Credit", use column mapping.
    - Otherwise fallback to heuristics (date in col0, avoid using long integers as amount).
    """
    raw_rows: list[dict[str, Any]] = []
    for table in tables:
        if not table:
            continue
        first_row = table[0]
        headers = [_cell(first_row, i) for i in range(len(first_row))] if table else []
        cols = _find_column_indices(headers)
        has_dc_col = "debit_credit" in cols
        start = 1 if (has_dc_col or _norm_header(_cell(table[0], 0)) in ("date", "particulars")) else 0

        for row in table[start:]:
            if not row:
                continue
            raw: dict[str, Any] = {}
            if has_dc_col:
                date_idx = cols.get("date", 0)
                part_idx = cols.get("particulars", 1)
                dc_idx = cols["debit_credit"]
                c0 = _cell(row, date_idx)
                part = _cell(row, part_idx)
                dc_cell = _cell(row, dc_idx)
                if _norm_header(c0) == "date" or _norm_header(part) in ("particulars", "particular"):
                    continue
                if not c0 and not dc_cell:
                    continue
                raw["date"] = c0 or None
                raw["narration"] = part or None
                raw["particulars"] = part or None
                amt_str, dr_cr = _parse_amount_dr_cr(dc_cell)
                if amt_str and dr_cr:
                    raw["amount"] = amt_str
                    raw["debit_credit"] = dr_cr
                else:
                    continue
                if not _looks_like_date(c0):
                    continue
            else:
                c0 = _cell(row, 0)
                c1 = _cell(row, 1)
                c2 = _cell(row, 2)
                c3 = _cell(row, 3)
                c4 = _cell(row, 4)
                if not c0:
                    continue
                raw["date"] = c0
                raw["narration"] = c1 or c2
                dc_cell = _first_currency_like([c2, c3, c4]) or _first_currency_like([c3, c4])
                if dc_cell:
                    amt_str, dr_cr = _parse_amount_dr_cr(dc_cell)
                    if amt_str and dr_cr:
                        raw["amount"] = amt_str
                        raw["debit_credit"] = dr_cr
                    else:
                        raw["withdrawal"] = _first_currency_like([c2, c3, c4])
                        raw["deposit"] = _first_currency_like([c3, c4])
                else:
                    raw["withdrawal"] = _first_currency_like([c2, c3, c4])
                    raw["deposit"] = _first_currency_like([c3, c4])
                if not _looks_like_date(c0) and not raw.get("withdrawal") and not raw.get("deposit") and not raw.get("amount"):
                    continue
            if raw.get("date") or raw.get("amount") or raw.get("withdrawal") or raw.get("deposit"):
                raw_rows.append(raw)
    return raw_rows
