"""Integration tests: accounts API."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def _create_primary_bank(client: AsyncClient, name: str = "Test Bank") -> str:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "bank", "name": name, "institution": "Test"},
    )
    assert r.status_code in (200, 201)
    return r.json()["id"]


async def test_create_wallet_without_parent(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "wallet", "name": "PhonePe Standalone", "institution": "PhonePe"},
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "wallet"
    assert data["parent_account_id"] is None


async def test_create_wallet_with_parent(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "wallet",
            "name": "Test Wallet",
            "institution": "Test",
            "parent_account_id": parent_id,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "wallet"
    assert data["parent_account_id"] == parent_id


async def test_create_loan_requires_parent(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "home",
            "name": "Orphan Loan",
            "sanctioned_amount": 5000000,
        },
    )
    assert r.status_code == 400


async def test_create_loan_with_parent(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "HDFC Savings")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "home",
            "name": "HDFC Home Loan",
            "institution": "HDFC",
            "sanctioned_amount": 5000000,
            "emi_amount": 40000,
            "tenure_months": 240,
            "start_date": "2024-01-01",
            "parent_account_id": parent_id,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "loan"
    assert data["loan_type"] == "home"
    assert data["sanctioned_amount"] == 5000000
    assert data["emi_amount"] == 40000
    assert data["parent_account_id"] == parent_id
    assert data["outstanding"] == 0
    assert data["credit_limit"] is None


async def test_loan_other_requires_description(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "other",
            "name": "Custom Loan",
            "parent_account_id": parent_id,
        },
    )
    assert r.status_code == 400


async def test_loan_metrics_after_payments(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Loan Metrics Bank")
    acc = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "personal",
            "name": "Personal Loan",
            "sanctioned_amount": 100000,
            "emi_amount": 10000,
            "tenure_months": 10,
            "start_date": "2025-06-01",
            "parent_account_id": parent_id,
        },
    )
    assert acc.status_code in (200, 201)
    account_id = acc.json()["id"]
    await client.post(
        "/v1/transactions",
        json={
            "amount": -100000,
            "transaction_date": "2026-01-01",
            "account_id": account_id,
            "nw_impact": "spending",
        },
    )
    await client.post(
        "/v1/transactions",
        json={
            "amount": 10000,
            "transaction_date": "2026-02-01",
            "account_id": account_id,
            "nw_impact": "liability_payment",
        },
    )
    r = await client.get("/v1/accounts")
    match = next(a for a in r.json() if a["id"] == account_id)
    assert match["outstanding"] == 90000
    assert match["amount_paid"] == 10000
    assert match["emi_paid_count"] == 1
    assert match["emi_pending_count"] == 9
    assert len(match["payment_history"]) == 1


async def test_loan_type_invalid_on_bank(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "bank", "name": "Bad Bank", "loan_type": "home"},
    )
    assert r.status_code == 400


async def test_list_accounts_includes_balance(client: AsyncClient) -> None:
    acc = await client.post(
        "/v1/accounts",
        json={"account_type": "bank", "name": "Balance Test Bank", "institution": "Test"},
    )
    assert acc.status_code in (200, 201)
    account_id = acc.json()["id"]
    await client.post(
        "/v1/transactions",
        json={
            "amount": 25000,
            "transaction_date": "2026-01-15",
            "account_id": account_id,
        },
    )
    r = await client.get("/v1/accounts")
    match = next(a for a in r.json() if a["id"] == account_id)
    assert match["balance"] == 25000


async def test_create_account_invalid_type(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={"account_type": "invalid", "name": "X", "institution": None},
    )
    assert r.status_code == 400


async def test_list_accounts(client: AsyncClient) -> None:
    r = await client.get("/v1/accounts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_create_credit_card_with_limit(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "HDFC Savings")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "HDFC Regalia",
            "institution": "HDFC",
            "credit_limit": 250000,
            "parent_account_id": parent_id,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["credit_limit"] == 250000
    assert data["sanctioned_amount"] is None


async def test_liabilities_api_deprecated(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/liabilities",
        json={
            "liability_type": "home_loan",
            "name": "Old API",
            "outstanding_amount": 1000,
        },
    )
    assert r.status_code == 410


async def test_delete_account_with_transactions_blocked(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Blocked Delete Bank")
    acc = await client.post(
        "/v1/accounts",
        json={
            "account_type": "wallet",
            "name": "Blocked Delete",
            "parent_account_id": parent_id,
        },
    )
    assert acc.status_code in (200, 201)
    account_id = acc.json()["id"]
    await client.post(
        "/v1/transactions",
        json={
            "amount": -100,
            "transaction_date": "2026-01-15",
            "account_id": account_id,
        },
    )
    r = await client.delete(f"/v1/accounts/{account_id}")
    assert r.status_code == 409


async def test_create_bank_with_opening_balance(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "Opening Balance Bank",
            "institution": "HDFC",
            "opening_balance": 50000,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["balance"] == 50000
    assert data["opening_balance"] == 50000
    assert data["transaction_count"] == 1

    txns = await client.get("/v1/transactions")
    assert txns.status_code == 200
    opening = next(
        t for t in txns.json() if t["account_id"] == data["id"] and t["source"] == "opening_balance"
    )
    assert float(opening["amount"]) == 50000
    assert opening["nw_impact"] == "transfer"


async def test_create_cash_with_opening_balance(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "cash",
            "name": "Opening Balance Cash",
            "opening_balance": 10000,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["balance"] == 10000
    assert data["opening_balance"] == 10000


async def test_opening_balance_rejected_on_wallet(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "wallet",
            "name": "PhonePe",
            "institution": "PhonePe",
            "parent_account_id": parent_id,
            "opening_balance": 5000,
        },
    )
    assert r.status_code == 400


async def test_opening_balance_rejected_on_loan(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "personal",
            "name": "Bad Loan OB",
            "parent_account_id": parent_id,
            "opening_balance": 5000,
        },
    )
    assert r.status_code == 400


async def test_update_opening_balance_upserts(client: AsyncClient) -> None:
    create = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "Upsert OB Bank",
            "opening_balance": 50000,
        },
    )
    assert create.status_code in (200, 201)
    account_id = create.json()["id"]

    update = await client.put(
        f"/v1/accounts/{account_id}",
        json={"opening_balance": 75000},
    )
    assert update.status_code == 200
    data = update.json()
    assert data["balance"] == 75000
    assert data["opening_balance"] == 75000
    assert data["transaction_count"] == 1

    txns = await client.get("/v1/transactions")
    opening = [t for t in txns.json() if t["account_id"] == account_id and t["source"] == "opening_balance"]
    assert len(opening) == 1
    assert float(opening[0]["amount"]) == 75000


async def test_clear_opening_balance(client: AsyncClient) -> None:
    create = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "Clear OB Bank",
            "opening_balance": 50000,
        },
    )
    assert create.status_code in (200, 201)
    account_id = create.json()["id"]

    update = await client.put(
        f"/v1/accounts/{account_id}",
        json={"opening_balance": 0},
    )
    assert update.status_code == 200
    data = update.json()
    assert data["balance"] == 0
    assert data["opening_balance"] is None
    assert data["transaction_count"] == 0


async def test_create_bank_with_details(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "HDFC Salary",
            "institution": "HDFC",
            "account_number": "123456789012",
            "ifsc_code": "hdfc0001234",
            "branch": "Koramangala",
            "account_notes": "Salary account",
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_number"] == "123456789012"
    assert data["ifsc_code"] == "HDFC0001234"
    assert data["branch"] == "Koramangala"
    assert data["account_notes"] == "Salary account"


async def test_bank_details_rejected_on_cash(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "cash",
            "name": "Cash Stash",
            "ifsc_code": "HDFC0001234",
        },
    )
    assert r.status_code == 400


async def test_invalid_ifsc_rejected(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "Bad IFSC Bank",
            "ifsc_code": "INVALID",
        },
    )
    assert r.status_code == 400


async def test_create_mutual_fund_requires_parent(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "Parag Parikh Flexi Cap",
            "institution": "Groww",
        },
    )
    assert r.status_code == 400


async def test_create_mutual_fund_with_opening_balance(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "MF Parent Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "Parag Parikh Flexi Cap",
            "institution": "Groww",
            "parent_account_id": parent_id,
            "opening_balance": 125000,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "mutual_fund"
    assert data["parent_account_id"] == parent_id
    assert data["balance"] == 125000
    assert data["opening_balance"] == 125000
    assert data["invested_amount"] == 125000
    assert data["current_value"] == 125000
    assert data["pnl_amount"] == 0
    assert data["pnl_percent"] == 0
    assert data["transaction_count"] == 1

    txns = await client.get("/v1/transactions")
    opening = next(
        t for t in txns.json() if t["account_id"] == data["id"] and t["source"] == "opening_balance"
    )
    assert float(opening["amount"]) == 125000
    assert opening["nw_impact"] == "transfer"


async def test_create_fixed_deposit_with_planning_fields(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "FD Parent Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "fixed_deposit",
            "name": "HDFC 12M FD",
            "institution": "HDFC",
            "parent_account_id": parent_id,
            "opening_balance": 500000,
            "start_date": "2026-01-01",
            "tenure_months": 12,
            "interest_rate": 7.25,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "fixed_deposit"
    assert data["start_date"] == "2026-01-01"
    assert data["tenure_months"] == 12
    assert float(data["interest_rate"]) == 7.25
    assert data["balance"] == 500000


async def test_create_mutual_fund_with_investment_pnl(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "P&L Parent Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "Index Fund",
            "parent_account_id": parent_id,
            "invested_amount": 100000,
            "current_value": 125000,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["investment_mode"] == "one_time"
    assert data["invested_amount"] == 100000
    assert data["current_value"] == 125000
    assert data["pnl_amount"] == 25000
    assert data["pnl_percent"] == 25


async def test_create_sip_mutual_fund(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "SIP Parent Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "Nifty SIP",
            "parent_account_id": parent_id,
            "investment_mode": "sip",
            "emi_amount": 5000,
            "due_day": 10,
            "start_date": "2025-01-10",
            "tenure_months": 12,
            "initial_sip_paid_count": 2,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["investment_mode"] == "sip"
    assert data["emi_amount"] == 5000
    assert data["due_day"] == 10
    assert data["sip_paid_count"] == 2
    assert data["sip_pending_count"] == 10
    assert len(data["payment_history"]) == 1
    assert data["payment_history"][0]["amount"] == 10000


async def test_sip_mutual_fund_tracks_installment_transactions(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "SIP Txn Bank")
    create = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "Flexi SIP",
            "parent_account_id": parent_id,
            "investment_mode": "sip",
            "emi_amount": 3000,
            "due_day": 5,
            "start_date": "2025-06-05",
            "tenure_months": 6,
        },
    )
    assert create.status_code in (200, 201)
    account_id = create.json()["id"]
    await client.post(
        "/v1/transactions",
        json={
            "amount": 3000,
            "transaction_date": "2026-01-05",
            "account_id": account_id,
            "category": "Investments",
            "nw_impact": "transfer",
        },
    )
    await client.post(
        "/v1/transactions",
        json={
            "amount": 3000,
            "transaction_date": "2026-02-05",
            "account_id": account_id,
            "category": "Investments",
            "nw_impact": "transfer",
        },
    )
    r = await client.get("/v1/accounts")
    match = next(a for a in r.json() if a["id"] == account_id)
    assert match["sip_paid_count"] == 2
    assert match["sip_pending_count"] == 4
    assert len(match["payment_history"]) == 2


async def test_sip_fields_rejected_on_one_time_mutual_fund(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "One-time MF Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "Lump Sum MF",
            "parent_account_id": parent_id,
            "investment_mode": "one_time",
            "emi_amount": 5000,
        },
    )
    assert r.status_code == 400


async def test_update_investment_current_value_recomputes_pnl(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Update P&L Bank")
    create = await client.post(
        "/v1/accounts",
        json={
            "account_type": "stock",
            "name": "Equity Portfolio",
            "parent_account_id": parent_id,
            "invested_amount": 200000,
            "current_value": 200000,
        },
    )
    account_id = create.json()["id"]
    update = await client.put(
        f"/v1/accounts/{account_id}",
        json={"current_value": 180000},
    )
    assert update.status_code == 200
    data = update.json()
    assert data["current_value"] == 180000
    assert data["pnl_amount"] == -20000
    assert data["pnl_percent"] == -10


async def test_investment_valuation_rejected_on_bank(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "Bad Bank Valuation",
            "invested_amount": 1000,
        },
    )
    assert r.status_code == 400


async def test_bank_details_rejected_on_mutual_fund(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "Bad MF Details",
            "parent_account_id": parent_id,
            "ifsc_code": "HDFC0001234",
        },
    )
    assert r.status_code == 400


async def test_create_credit_card_with_due_day(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "CC Due Parent")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "HDFC Regalia",
            "institution": "HDFC",
            "parent_account_id": parent_id,
            "credit_limit": 500000,
            "due_day": 15,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["due_day"] == 15


async def test_due_day_cleared_when_type_changes_from_credit_card(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "CC Type Change Bank")
    create = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "Switch Me",
            "parent_account_id": parent_id,
            "due_day": 10,
        },
    )
    assert create.status_code in (200, 201)
    account_id = create.json()["id"]

    update = await client.put(
        f"/v1/accounts/{account_id}",
        json={"account_type": "wallet"},
    )
    assert update.status_code == 200
    assert update.json()["due_day"] is None


async def test_loan_requires_start_date_when_emi_and_tenure_set(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Loan Start Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "home",
            "name": "Home Loan Missing Start",
            "parent_account_id": parent_id,
            "emi_amount": 40000,
            "tenure_months": 240,
        },
    )
    assert r.status_code == 400


async def test_loan_with_start_date_emi_tenure(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Loan Start OK Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "home",
            "name": "Home Loan With Start",
            "parent_account_id": parent_id,
            "emi_amount": 40000,
            "tenure_months": 240,
            "start_date": "2024-06-01",
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["start_date"] == "2024-06-01"
    assert data["emi_amount"] == 40000
    assert data["tenure_months"] == 240


async def test_create_mutual_fund_with_folio(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Folio Parent Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "mutual_fund",
            "name": "MF With Folio",
            "parent_account_id": parent_id,
            "folio_number": "1234567890",
        },
    )
    assert r.status_code in (200, 201)
    assert r.json()["folio_number"] == "1234567890"


async def test_folio_rejected_on_stock(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client)
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "stock",
            "name": "Bad Stock Folio",
            "parent_account_id": parent_id,
            "folio_number": "123456",
        },
    )
    assert r.status_code == 400


async def test_create_stock_with_demat_id(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Demat Parent Bank")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "stock",
            "name": "Zerodha Holdings",
            "institution": "Zerodha",
            "parent_account_id": parent_id,
            "demat_id": "IN3001234567890",
        },
    )
    assert r.status_code in (200, 201)
    assert r.json()["demat_id"] == "IN3001234567890"


async def test_create_credit_card_with_initial_credit_used(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "CC Initial Parent")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "HDFC Regalia",
            "parent_account_id": parent_id,
            "credit_limit": 200000,
            "initial_credit_used": 35000,
            "initial_credit_used_date": "2026-05-15",
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["initial_credit_used"] == 35000
    assert data["initial_credit_used_date"] == "2026-05-15"
    assert data["credit_used"] == 35000

    txns = await client.get("/v1/transactions")
    seed = [
        t
        for t in txns.json()
        if t["account_id"] == data["id"] and t["source"] == "initial_credit_used"
    ]
    assert len(seed) == 1
    assert float(seed[0]["amount"]) == -35000
    assert seed[0]["nw_impact"] == "spending"
    assert seed[0]["transaction_date"] == "2026-05-15"


async def test_initial_credit_used_requires_date(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "CC No Date Parent")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "ICICI Coral",
            "parent_account_id": parent_id,
            "initial_credit_used": 10000,
        },
    )
    assert r.status_code == 400


async def test_initial_credit_used_rejected_on_bank(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "bank",
            "name": "Bad Initial CC Bank",
            "initial_credit_used": 5000,
            "initial_credit_used_date": "2026-05-01",
        },
    )
    assert r.status_code == 400


async def test_update_initial_credit_used(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "CC Update Parent")
    create = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "Update CC",
            "parent_account_id": parent_id,
            "initial_credit_used": 20000,
            "initial_credit_used_date": "2026-04-01",
        },
    )
    assert create.status_code in (200, 201)
    account_id = create.json()["id"]

    update = await client.put(
        f"/v1/accounts/{account_id}",
        json={
            "initial_credit_used": 30000,
            "initial_credit_used_date": "2026-05-01",
        },
    )
    assert update.status_code == 200
    data = update.json()
    assert data["initial_credit_used"] == 30000
    assert data["credit_used"] == 30000

    txns = await client.get("/v1/transactions")
    seed = [
        t
        for t in txns.json()
        if t["account_id"] == account_id and t["source"] == "initial_credit_used"
    ]
    assert len(seed) == 1
    assert float(seed[0]["amount"]) == -30000


async def test_update_credit_card_with_null_opening_balance_no_500(client: AsyncClient) -> None:
    """Frontend used to send opening_balance: null on CC edit — must not 500."""
    parent_id = await _create_primary_bank(client, "CC Edit Parent")
    create = await client.post(
        "/v1/accounts",
        json={
            "account_type": "credit_card",
            "name": "Edit CC",
            "parent_account_id": parent_id,
            "credit_limit": 100000,
        },
    )
    assert create.status_code in (200, 201)
    account_id = create.json()["id"]

    update = await client.put(
        f"/v1/accounts/{account_id}",
        json={
            "name": "Edit CC Updated",
            "opening_balance": None,
            "credit_limit": 120000,
        },
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Edit CC Updated"


async def test_create_loan_with_initial_emi_paid_count(client: AsyncClient) -> None:
    parent_id = await _create_primary_bank(client, "Loan Initial Parent")
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "loan",
            "loan_type": "personal",
            "name": "Mid Tenure Loan",
            "sanctioned_amount": 1000000,
            "emi_amount": 100000,
            "tenure_months": 10,
            "start_date": "2025-06-01",
            "initial_emi_paid_count": 3,
            "parent_account_id": parent_id,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["initial_emi_paid_count"] == 3
    assert data["outstanding"] == 700000
    assert data["emi_paid_count"] == 3
    assert data["emi_pending_count"] == 7


async def test_create_epf_without_parent_and_opening_balance(client: AsyncClient) -> None:
    """REG-F058: EPF is standalone; opening balance seeds holdings."""
    r = await client.post(
        "/v1/accounts",
        json={
            "account_type": "epf",
            "name": "Acme Corp EPF",
            "institution": "Acme Corp",
            "folio_number": "101234567890",
            "opening_balance": 350000,
        },
    )
    assert r.status_code in (200, 201)
    data = r.json()
    assert data["account_type"] == "epf"
    assert data["parent_account_id"] is None
    assert data["folio_number"] == "101234567890"
    assert data["balance"] == 350000
    assert data["opening_balance"] == 350000
    assert data["transaction_count"] == 1

    txns = await client.get("/v1/transactions")
    opening = next(
        t for t in txns.json() if t["account_id"] == data["id"] and t["source"] == "opening_balance"
    )
    assert float(opening["amount"]) == 350000
    assert opening["nw_impact"] == "transfer"


async def test_epf_rejects_demat_accepts_uan(client: AsyncClient) -> None:
    """REG-F059: EPF uses folio_number as UAN; demat_id not allowed."""
    bad = await client.post(
        "/v1/accounts",
        json={
            "account_type": "epf",
            "name": "Bad EPF",
            "demat_id": "IN3001234567890",
        },
    )
    assert bad.status_code == 400

    good = await client.post(
        "/v1/accounts",
        json={
            "account_type": "epf",
            "name": "Good EPF",
            "folio_number": "101234567890",
            "opening_balance": 100000,
        },
    )
    assert good.status_code in (200, 201)
    assert good.json()["folio_number"] == "101234567890"
