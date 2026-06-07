"""Unit tests for mutual fund investment mode validation."""
import pytest

from app.services.mf_investment_mode import (
    normalize_investment_mode,
    validate_investment_mode,
)


def test_normalize_investment_mode():
    assert normalize_investment_mode("sip") == "sip"
    assert normalize_investment_mode("ONE_TIME") == "one_time"


def test_normalize_investment_mode_rejects_invalid():
    with pytest.raises(ValueError, match="investment_mode must be one of"):
        normalize_investment_mode("monthly")


def test_sip_requires_schedule_fields():
    with pytest.raises(ValueError, match="emi_amount is required"):
        validate_investment_mode("mutual_fund", "sip")
    with pytest.raises(ValueError, match="due_day is required"):
        validate_investment_mode(
            "mutual_fund",
            "sip",
            emi_amount=5000,
        )
    with pytest.raises(ValueError, match="start_date is required"):
        validate_investment_mode(
            "mutual_fund",
            "sip",
            emi_amount=5000,
            due_day=10,
        )


def test_one_time_rejects_sip_fields():
    with pytest.raises(ValueError, match="emi_amount applies only to SIP"):
        validate_investment_mode("mutual_fund", "one_time", emi_amount=5000)


def test_investment_mode_only_for_mutual_fund():
    with pytest.raises(ValueError, match="investment_mode applies only"):
        validate_investment_mode("stock", "sip")
