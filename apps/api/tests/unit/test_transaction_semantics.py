"""Unit tests for transaction nw_impact classification."""
import pytest
from decimal import Decimal

from app.services.transaction_semantics import NwImpact, classify_transaction

pytestmark = pytest.mark.unit


def test_rent_is_spending():
    assert classify_transaction(
        Decimal("-22000"),
        merchant="NEFT DR-RENT-PROP MGMT",
        category="Housing",
        account_type="bank",
    ) == NwImpact.spending


def test_emi_is_liability_payment():
    assert classify_transaction(
        Decimal("-28500"),
        merchant="ACH DR-HDFC HOME LOAN EMI",
        category="EMI",
        account_type="bank",
    ) == NwImpact.liability_payment


def test_sip_is_transfer():
    assert classify_transaction(
        Decimal("-10000"),
        merchant="ACH DR-SBI MF SIP GROWTH",
        category="Investments",
        account_type="bank",
    ) == NwImpact.transfer


def test_billpay_is_liability_payment():
    assert classify_transaction(
        Decimal("-20238"),
        merchant="BILLPAY-CREDIT CARD HDFC",
        category="Bills",
        account_type="bank",
    ) == NwImpact.liability_payment


def test_salary_is_income():
    assert classify_transaction(
        Decimal("125000"),
        merchant="NEFT CR-SALARY-ACME TECH PVT LTD",
        category="Income",
        account_type="bank",
    ) == NwImpact.income


def test_cc_swipe_is_spending():
    assert classify_transaction(
        Decimal("-649"),
        merchant="NETFLIX.COM",
        account_type="credit_card",
    ) == NwImpact.spending


def test_refund_keyword():
    assert classify_transaction(
        Decimal("500"),
        merchant="AMAZON REFUND",
        raw_description="REFUND FOR ORDER",
        account_type="bank",
    ) == NwImpact.refund
