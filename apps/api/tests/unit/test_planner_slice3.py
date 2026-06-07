"""Unit tests: Slice 3 keyword routing in planner."""
import pytest

from app.agents.planner import (
    _detect_add_expense,
    _detect_create_account_guided,
    _detect_explain_transaction,
    _detect_record_transfer,
    _detect_recategorize_transaction,
)
from app.core.schemas import Intent

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "message",
    [
        "record SIP 5000 for HDFC MF",
        "transfer 5000 to my mutual fund",
        "fund my SIP 3000",
        "paid SIP 5000",
        "record transfer 2500 to Nifty SIP",
    ],
)
def test_detect_record_transfer(message: str) -> None:
    result = _detect_record_transfer(message)
    assert result is not None
    assert result.intent == Intent.record_transfer
    assert result.steps[0].action == "insert_transfer"
    assert result.steps[0].params["amount"] > 0


def test_record_transfer_not_add_expense() -> None:
    transfer = _detect_record_transfer("record SIP 5000 for HDFC MF")
    expense = _detect_add_expense("record SIP 5000 for HDFC MF")
    assert transfer is not None
    assert expense is None


def test_detect_record_transfer_extracts_investment_name() -> None:
    result = _detect_record_transfer("record SIP 5000 for HDFC MF")
    assert result is not None
    assert result.steps[0].params.get("investment_name") == "HDFC MF"


# ── S3.2 explain_transaction ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "message",
    [
        "explain this charge",
        "what is this transaction?",
        "show recent Swiggy transactions",
        "what did I spend at Zomato",
        "explain the charge from Netflix",
    ],
)
def test_detect_explain_transaction(message: str) -> None:
    result = _detect_explain_transaction(message)
    assert result is not None
    assert result.intent == Intent.explain_transaction
    assert result.steps[0].action == "explain_transaction"


def test_explain_transaction_no_match() -> None:
    assert _detect_explain_transaction("what is my net worth?") is None


# ── S3.3 recategorize_transaction ───────────────────────────────────────────

@pytest.mark.parametrize(
    "message,expected_cat",
    [
        ("recategorize Netflix to Entertainment", "Entertainment"),
        ("change category of Swiggy to Food", "Food"),
        ("classify Uber as Transport", "Transport"),
    ],
)
def test_detect_recategorize(message: str, expected_cat: str) -> None:
    result = _detect_recategorize_transaction(message)
    assert result is not None
    assert result.intent == Intent.recategorize_transaction
    assert result.steps[0].params["new_category"].lower() == expected_cat.lower()


def test_recategorize_no_match() -> None:
    assert _detect_recategorize_transaction("add expense 500 coffee") is None


# ── S3.3 create_account_guided ───────────────────────────────────────────────

@pytest.mark.parametrize(
    "message,exp_type",
    [
        ("add SIP account for Nifty 50", "mutual_fund"),
        ("create mutual fund account", "mutual_fund"),
        ("add EPF account", "epf"),
        ("create FD account", "fixed_deposit"),
    ],
)
def test_detect_create_account_guided(message: str, exp_type: str) -> None:
    result = _detect_create_account_guided(message)
    assert result is not None
    assert result.intent == Intent.create_account_guided
    assert result.steps[0].params["account_type"] == exp_type


def test_create_account_guided_sip_extracts_amount() -> None:
    result = _detect_create_account_guided("add SIP account 5000 for HDFC Top 200")
    assert result is not None
    assert result.steps[0].params.get("emi_amount") == 5000.0
