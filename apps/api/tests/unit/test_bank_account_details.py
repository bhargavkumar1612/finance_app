"""Unit tests: bank account detail validation."""
import pytest

from app.services.bank_account_details import normalize_ifsc, validate_bank_details

pytestmark = pytest.mark.unit


def test_normalize_ifsc_uppercases():
    assert normalize_ifsc("hdfc0001234") == "HDFC0001234"


def test_invalid_ifsc_raises():
    with pytest.raises(ValueError, match="IFSC"):
        normalize_ifsc("BAD")


def test_bank_details_rejected_on_cash():
    with pytest.raises(ValueError, match="ifsc_code"):
        validate_bank_details("cash", account_number=None, ifsc_code="HDFC0001234", branch=None, account_notes=None)
