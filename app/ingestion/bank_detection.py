"""
Detect bank from CSV header row or PDF first-page text.
"""
import re
from typing import Sequence

# Normalize header: lower, strip, collapse spaces
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


# CSV: column names that indicate bank
CSV_SIGNATURES: dict[str, Sequence[str]] = {
    "hdfc": ["date", "narration", "withdrawal", "deposit", "balance", "chq", "value date"],
    "icici": ["transaction date", "value date", "description", "debit", "credit", "balance"],
    "sbi": ["value date", "transaction date", "description", "debit", "credit", "balance"],
    "axis": ["transaction date", "description", "debit", "credit", "balance"],
}


def detect_bank_from_csv_headers(headers: Sequence[str]) -> str | None:
    """First row of CSV as column names. Returns bank key or None."""
    norm_headers = set(_norm(h) for h in headers if h)
    for bank, sigs in CSV_SIGNATURES.items():
        if any(_norm(s) in norm_headers for s in sigs):
            # Prefer HDFC/ICICI if multiple match (order of dict)
            return bank
    return None


# PDF: keywords on first page
PDF_SIGNATURES: dict[str, Sequence[str]] = {
    "hdfc": ["hdfc bank", "hdfc bank ltd"],
    "icici": ["icici bank"],
    "sbi": ["state bank of india", "sbi"],
    "axis": ["axis bank"],
}


def detect_bank_from_text(text: str) -> str | None:
    """First page or header text from PDF. Returns bank key or None."""
    if not text:
        return None
    t = _norm(text)[:2000]
    for bank, sigs in PDF_SIGNATURES.items():
        if any(s in t for s in sigs):
            return bank
    return None
