"""Unit tests: affordability what-if params."""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.affordability import calculate_affordability

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_affordability_with_hypothetical_income_and_target_emi() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=lambda: Decimal(0)))

    with patch("app.services.affordability.average_monthly_spending", AsyncMock(return_value=40000.0)), patch(
        "app.services.affordability.monthly_commitments_breakdown",
        AsyncMock(return_value={"total_commitments": 35000, "loan_emis": 35000}),
    ), patch(
        "app.services.affordability.compute_net_worth",
        AsyncMock(return_value={"net_worth": 539324}),
    ):
        result = await calculate_affordability(
            session,
            user_id="00000000-0000-0000-0000-000000000001",
            target_emi=20000,
            hypothetical_monthly_income=190000,
        )

    assert result["monthly_income"] == 190000
    assert result["target_emi"] == 20000
    assert result["can_afford_target"] is True
    assert "Yes" in result["message"]
