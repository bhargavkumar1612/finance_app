"""Unit tests: account UI grouping and contribution amounts."""
import pytest

from app.services.account_grouping import (
    account_balance_side,
    account_contribution_amount,
    account_ui_group,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("account_type", "expected"),
    [
        ("bank", "asset"),
        ("cash", "asset"),
        ("wallet", "asset"),
        ("mutual_fund", "asset"),
        ("fixed_deposit", "asset"),
        ("recurring_deposit", "asset"),
        ("stock", "asset"),
        ("epf", "asset"),
        ("credit_card", "liability"),
        ("loan", "liability"),
    ],
)
def test_account_balance_side(account_type, expected):
    assert account_balance_side(account_type) == expected


@pytest.mark.parametrize(
    ("account_type", "expected"),
    [
        ("bank", "cash_wallets"),
        ("cash", "cash_wallets"),
        ("wallet", "cash_wallets"),
        ("mutual_fund", "investments"),
        ("fixed_deposit", "investments"),
        ("recurring_deposit", "investments"),
        ("stock", "investments"),
        ("epf", "investments"),
        ("credit_card", "credit_cards"),
        ("loan", "loans"),
    ],
)
def test_account_ui_group(account_type, expected):
    assert account_ui_group(account_type) == expected


def test_contribution_uses_balance_for_assets():
    assert account_contribution_amount("bank", balance=50000) == 50000
    assert account_contribution_amount("mutual_fund", balance=120000) == 120000


def test_contribution_uses_current_value_for_holdings():
    assert account_contribution_amount(
        "mutual_fund",
        balance=100000,
        current_value=140000,
    ) == 140000


def test_contribution_uses_credit_used_not_limit():
    assert account_contribution_amount(
        "credit_card",
        balance=0,
        credit_used=25000,
    ) == 25000


def test_contribution_uses_outstanding_for_loans():
    assert account_contribution_amount(
        "loan",
        balance=0,
        outstanding=1500000,
    ) == 1500000


def test_contribution_defaults_to_zero():
    assert account_contribution_amount("bank") == 0
    assert account_contribution_amount("credit_card") == 0
    assert account_contribution_amount("loan") == 0
