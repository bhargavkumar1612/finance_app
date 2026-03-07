"""
PDF router: is_scanned check, extract tables, dispatch to bank-specific parser.
"""
from typing import Any

from app.ingestion.bank_detection import detect_bank_from_text


def is_scanned(content: bytes) -> bool:
    """True if PDF has no or very little extractable text (likely scanned)."""
    try:
        import pdfplumber
    except ImportError:
        return True
    try:
        import io
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if not pdf.pages:
                return True
            text = pdf.pages[0].extract_text() or ""
            return len(text.strip()) < 20
    except Exception:
        return True


def extract_tables_from_pdf(content: bytes) -> list[list[list[str | None]]]:
    """Extract all tables from all pages. Returns list of tables; each table is list of rows; row is list of cell values."""
    try:
        import io
        import pdfplumber
    except ImportError:
        return []
    out = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    out.extend(tables)
    except Exception:
        pass
    return out


def parse_pdf(
    content: bytes,
    filename: str | None = None,
    bank_hint: str | None = None,
) -> list[dict[str, Any]]:
    """
    Extract raw rows from PDF. If scanned, returns empty. Else tables -> bank parser.
    """
    if is_scanned(content):
        return []
    tables = extract_tables_from_pdf(content)
    if not tables:
        return []
    # First page text for bank detection
    try:
        import io
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            first_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
    except Exception:
        first_text = ""
    bank = bank_hint or detect_bank_from_text(first_text)
    if bank == "hdfc":
        from app.ingestion.pdf_parsers.hdfc_pdf import tables_to_raw_rows
        return tables_to_raw_rows(tables)
    # Default: try HDFC-style
    from app.ingestion.pdf_parsers.hdfc_pdf import tables_to_raw_rows
    return tables_to_raw_rows(tables)
