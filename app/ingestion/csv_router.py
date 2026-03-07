"""
CSV router: dispatch by bank (hint or detection), return list of raw row dicts.
"""
from typing import Any

from app.ingestion.csv_parsers.hdfc import parse_csv


def parse_csv_file(content: bytes, filename: str | None = None, bank_hint: str | None = None) -> list[dict[str, Any]]:
    """
    Parse CSV content. If bank_hint (e.g. 'hdfc') use it; else detect from header.
    filename unused for CSV; kept for API consistency.
    """
    return parse_csv(content, bank_hint=bank_hint)
