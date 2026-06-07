"""Unit tests: investment reference ID validation."""
import pytest

from app.services.investment_account_details import validate_investment_details

pytestmark = pytest.mark.unit


def test_folio_rejected_on_stock():
    with pytest.raises(ValueError, match="folio_number"):
        validate_investment_details("stock", folio_number="123456", demat_id=None)


def test_demat_rejected_on_mutual_fund():
    with pytest.raises(ValueError, match="demat_id"):
        validate_investment_details("mutual_fund", folio_number=None, demat_id="IN300123")


def test_uan_accepted_on_epf():
    validate_investment_details("epf", folio_number="101234567890", demat_id=None)


def test_demat_rejected_on_epf():
    with pytest.raises(ValueError, match="demat_id"):
        validate_investment_details("epf", folio_number=None, demat_id="IN300123")
