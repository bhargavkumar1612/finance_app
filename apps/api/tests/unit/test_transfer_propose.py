"""Unit tests: transfer propose validation helpers."""
from uuid import uuid4

import pytest

from app.agents.ledger_agent import LedgerError, _insert_transfer, _resolve_investment_account, _resolve_parent_bank
from app.db.models import Account

pytestmark = pytest.mark.unit


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value if isinstance(self._value, list) else []


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _query):
        if not self._responses:
            raise RuntimeError("no more fake responses")
        return _FakeResult(self._responses.pop(0))


@pytest.mark.asyncio
async def test_resolve_investment_account_no_accounts() -> None:
    session = _FakeSession([[]])
    with pytest.raises(LedgerError, match="No investment account"):
        await _resolve_investment_account(session, uuid4(), {})


@pytest.mark.asyncio
async def test_resolve_parent_bank_missing_parent() -> None:
    mf = Account(
        name="Nifty SIP",
        account_type="mutual_fund",
        investment_mode="sip",
        parent_account_id=None,
    )
    session = _FakeSession([])
    with pytest.raises(LedgerError, match="no linked bank"):
        await _resolve_parent_bank(session, uuid4(), mf)


@pytest.mark.asyncio
async def test_insert_transfer_atomic_rollback_on_bad_account() -> None:
    """If a leg has an invalid account_id, the whole transfer is rejected."""
    from unittest.mock import AsyncMock, MagicMock, patch

    user_id = uuid4()

    real_session = AsyncMock()
    real_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    real_session.add = MagicMock()
    real_session.commit = AsyncMock()
    real_session.refresh = AsyncMock()

    bad_params = {
        "legs": [
            {
                "account_id": str(uuid4()),
                "amount": -5000,
                "merchant": "SIP — Test MF",
            },
            {
                "account_id": str(uuid4()),
                "amount": 5000,
                "merchant": "SIP — Test MF",
            },
        ],
        "transaction_date": "2026-06-07",
    }
    with pytest.raises(LedgerError, match="not found"):
        await _insert_transfer(real_session, user_id, bad_params, None)

    real_session.commit.assert_not_awaited()
