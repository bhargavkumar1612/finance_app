"""Unit tests: account balance metrics."""
import pytest

from app.services.account_types import (
    LOAN_DETAIL_TYPES,
    LOAN_TYPES,
    DERIVED_TYPES,
    PARENT_LINKABLE_TYPES,
    PARENT_REQUIRED_TYPES,
)

pytestmark = pytest.mark.unit


def test_loan_account_type():
    assert "loan" in LOAN_TYPES
    assert "loan" in DERIVED_TYPES


def test_loan_detail_types():
    assert "vehicle" in LOAN_DETAIL_TYPES
    assert "education" in LOAN_DETAIL_TYPES
    assert "other" in LOAN_DETAIL_TYPES


def test_parent_link_rules():
    assert "credit_card" in PARENT_REQUIRED_TYPES
    assert "loan" in PARENT_REQUIRED_TYPES
    assert "wallet" not in PARENT_REQUIRED_TYPES
    assert "wallet" in PARENT_LINKABLE_TYPES
