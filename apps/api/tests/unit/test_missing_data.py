"""Unit tests for proactive hint ordering."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.missing_data import check_missing_data


@pytest.mark.asyncio
async def test_sip_hint_prioritized_over_rent_and_salary() -> None:
    """Overdue SIP hints appear even when salary/rent/EMI hints also apply."""
    user_id = uuid4()
    sip_acc = MagicMock()
    sip_acc.name = "Late SIP"
    sip_acc.due_day = 5
    sip_acc.account_type = "mutual_fund"

    session = AsyncMock()
    # income miss, rent miss, no loans, one SIP account
    session.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # income
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # rent
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: []))),  # loans
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [sip_acc]))),  # sips
        ]
    )

    with patch("app.services.missing_data.is_sip_account", return_value=True), patch(
        "app.services.missing_data.compute_sip_schedule",
        new=AsyncMock(return_value={"payment_history": []}),
    ), patch("app.services.missing_data.date") as mock_date:
        mock_date.today.return_value = date(2026, 6, 10)
        mock_date.side_effect = lambda *a, **k: date(*a, **k)
        hints = await check_missing_data(session, user_id)

    assert hints[0] == "Log SIP payment for Late SIP"
    assert "Add this month's salary" in hints
    assert len(hints) <= 5
