"""Unit tests: initial credit used seed transaction."""
import pytest

from app.services.initial_credit_used import INITIAL_CREDIT_USED_SOURCE

pytestmark = pytest.mark.unit


def test_initial_credit_used_source_constant():
    assert INITIAL_CREDIT_USED_SOURCE == "initial_credit_used"
