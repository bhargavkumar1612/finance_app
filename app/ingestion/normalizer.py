"""
Normalizer: raw row (from any parser) -> NormalizedTransaction.
Handles Indian number format, DR/CR/parentheses, date parsing.
"""
import re
from datetime import date
from decimal import Decimal
from typing import Any

from app.core.schemas import NormalizedTransaction
from app.services.categorization import auto_categorize, extract_upi_id


# Indian: 1,23,456.00 or 123456 or (123) for negative
_AMOUNT_CLEAN = re.compile(r"[\s,]")
_PAREN_NEGATIVE = re.compile(r"^\((.+)\)$")

# Dates: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
_DATE_PATTERNS = [
    (re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"), lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),  # YYYY-MM-DD
    (re.compile(r"^(\d{2})-(\d{2})-(\d{4})$"), lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)))),  # DD-MM-YYYY
    (re.compile(r"^(\d{2})/(\d{2})/(\d{4})$"), lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)))),  # DD/MM/YYYY
    (re.compile(r"^(\d{4})/(\d{2})/(\d{2})$"), lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),  # YYYY/MM/DD
]


def _parse_amount(value: Any, debit_credit: str | None = None) -> Decimal | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.upper() in ("DR", "CR", "-", ""):
        return None
    # Parentheses = negative
    m = _PAREN_NEGATIVE.match(s)
    if m:
        s = "-" + m.group(1)
    s = _AMOUNT_CLEAN.sub("", s)
    try:
        amt = Decimal(s)
    except Exception:
        return None
    if debit_credit:
        dc = debit_credit.upper()
        if dc in ("DR", "DEBIT", "WITHDRAWAL", "CHQ", "WITHDR"):
            amt = -abs(amt)
        elif dc in ("CR", "CREDIT", "DEPOSIT", "DEP"):
            amt = abs(amt)
    return amt


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()[:10]
    for pat, groups in _DATE_PATTERNS:
        m = pat.match(s)
        if m:
            try:
                y, mo, d = groups(m)
                return date(y, mo, d)
            except (ValueError, TypeError):
                continue
    return None


def _trim_merchant(s: str | None, max_len: int = 500) -> str | None:
    if s is None:
        return None
    t = s.strip()
    if not t:
        return None
    return t[:max_len] if len(t) > max_len else t


def normalize_row(raw: dict[str, Any]) -> NormalizedTransaction:
    """
    Raw row from parser: date, amount or withdrawal/deposit, debit_credit, narration/description, etc.
    Returns NormalizedTransaction (debit = negative amount).
    """
    debit_credit = raw.get("debit_credit") or raw.get("type") or raw.get("dr_cr")
    amount = raw.get("amount")
    if amount is None:
        withdrawal = raw.get("withdrawal", raw.get("Withdrawal", raw.get("debit")))
        deposit = raw.get("deposit", raw.get("Deposit", raw.get("credit")))
        if withdrawal is not None and str(withdrawal).strip():
            amount = _parse_amount(withdrawal, "DR")
        elif deposit is not None and str(deposit).strip():
            amount = _parse_amount(deposit, "CR")
        else:
            amount = _parse_amount(raw.get("value", raw.get("Value")), debit_credit)
    else:
        amount = _parse_amount(amount, debit_credit)
    if amount is None:
        amount = Decimal(0)
    date_val = _parse_date(
        raw.get("date") or raw.get("Date") or raw.get("transaction_date") or raw.get("value_date")
    )
    if date_val is None:
        date_val = date.today()
    merchant = _trim_merchant(
        raw.get("merchant") or raw.get("narration") or raw.get("Narration")
        or raw.get("particulars") or raw.get("description") or raw.get("Description")
    )
    raw_desc = _trim_merchant(
        raw.get("raw_description") or raw.get("description") or raw.get("narration"),
        max_len=2000,
    )
    confidence = raw.get("confidence")
    if confidence is not None:
        try:
            confidence = Decimal(str(confidence))
        except Exception:
            confidence = None
            
    # Phase 5: Auto-categorize and extract UPI
    upi_id = extract_upi_id(raw_desc or merchant or "")
    if upi_id and merchant:
        merchant = f"{merchant} ({upi_id})"
        
    suggested_category = auto_categorize(merchant or "", raw_desc or "")
    
    return NormalizedTransaction(
        amount=amount,
        date=date_val,
        merchant=merchant,
        raw_description=raw_desc,
        reference=raw.get("reference") or raw.get("Reference"),
        confidence=confidence,
        suggested_category=suggested_category,
    )
