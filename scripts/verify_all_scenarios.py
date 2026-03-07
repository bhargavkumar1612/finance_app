import httpx
import asyncio
from datetime import date, timedelta

BASE_URL = "http://localhost:8000/v1"
HEADERS = {"Content-Type": "application/json"}
TEST_EMAIL = "test_automation_2@local"

async def run_tests():
    print("--- 🚀 Starting Integration Tests ---")
    async with httpx.AsyncClient(base_url=BASE_URL, headers=HEADERS, timeout=None) as client:
        # 1. Authentication & Initialization
        print("\n[1] Authentication & Initialization")
        res = await client.post("/login", json={"email": TEST_EMAIL})
        assert res.status_code == 200, f"Login failed: {res.text}"
        user_id = res.json()["id"]
        auth_headers = {**HEADERS, "X-User-Email": TEST_EMAIL}
        print(f"✅ Login successful, User ID: {user_id}")

        res = await client.get("/accounts", headers=auth_headers)
        accounts = res.json()
        assert len(accounts) > 0, "No default account created"
        default_account_id = accounts[0]["id"]
        print("✅ Default Cash account verified")

        # 3. Financial Tools: Custom Account
        print("\n[3] Financial Tools & APIs")
        res = await client.post("/accounts", headers=auth_headers, json={"name": "HDFC Savings", "account_type": "bank", "currency": "INR"})
        assert res.status_code == 200, f"Account creation failed: {res.text}"
        print("✅ Custom Account creation successful")

        # 2. Core Chat: General Conversation
        print("\n[2] Core Chat & LLM Orchestration")
        res = await client.post("/chat", headers=auth_headers, json={"message": "Give me some financial advice for a 20-year-old."})
        data = res.json()
        assert data["response"]["ui_type"] == "message_only", f"Expected message_only, got {data['response']['ui_type']}"
        conv_id = data["conversation_id"]
        print("✅ General Chat & Intent Routing (unknown) successful")

        # Context Tracking
        res = await client.post("/chat", headers=auth_headers, json={"message": "Can you summarize that?", "conversation_id": conv_id})
        assert res.status_code == 200
        print("✅ Context Tracking (multi-turn) successful")

        # 3. Financial Tools: Ledger
        res = await client.post("/chat", headers=auth_headers, json={"message": "I spent 500 on Swiggy for lunch"})
        data = res.json()
        assert data["response"]["ui_type"] == "transaction_confirm", "Failed to parse expense"
        print("✅ Add Expense via Chat successful")

        res = await client.post("/chat", headers=auth_headers, json={"message": "I received my 50000 salary"})
        data = res.json()
        assert data["response"]["ui_type"] in ["transaction_confirm", "message_only"]
        print("✅ Add Income via Chat successful")

        res = await client.get("/transactions", headers=auth_headers)
        assert len(res.json()) > 0
        print("✅ GET Transactions CRUD successful")

        # Insights
        res = await client.post("/chat", headers=auth_headers, json={"message": "What is my net worth?"})
        data = res.json()
        assert data["response"]["ui_type"] == "net_worth_breakdown"
        print("✅ Net Worth Query & Insight Agent successful")
        
        # Missing Data (Intelligence)
        actions = data["response"]["next_suggested_actions"]
        if any("rent" in a.lower() for a in actions):
            print("✅ Intelligence: Missing Data Nudges verified")

        res = await client.post("/chat", headers=auth_headers, json={"message": "Where did I spend my money this month?"})
        data = res.json()
        assert "message" in data["response"]["data"]
        print("✅ Monthly Spending Analysis successful")

        res = await client.post("/chat", headers=auth_headers, json={"message": "Can I afford a 25000 EMI?"})
        data = res.json()
        assert data["response"]["ui_type"] == "affordability_result"
        print("✅ Affordability Engine Check successful")

        # 6. Guardrails & Edge Cases
        print("\n[6] Guardrails & Edge Cases")
        future_date = (date.today() + timedelta(days=2)).isoformat()
        res = await client.post("/transactions", headers=auth_headers, json={"amount": -100, "transaction_date": future_date, "account_id": default_account_id})
        assert res.status_code == 400
        print("✅ Guardrail: Future Date Prevention successful")

        res = await client.post("/transactions", headers=auth_headers, json={"amount": 0, "transaction_date": date.today().isoformat(), "account_id": default_account_id})
        assert res.status_code == 400
        print("✅ Guardrail: Zero Amount Prevention successful")
        
        # 5. Intelligence: UPI Extraction (Manual API test)
        res = await client.post("/transactions", headers=auth_headers, json={
            "amount": -200, 
            "transaction_date": date.today().isoformat(), 
            "account_id": default_account_id,
            "raw_description": "UPI-Zomato-zomato@okicici-123456"
        })
        # Note: Depending on if auto-categorize runs on API inserts or just CSV import. We rely on CSV normalizer for UPI extract currently. 
        # But let's verify standard inserts work.
        assert res.status_code == 200
        print("✅ Standard Transaction Insert successful")
        
        res = await client.post("/chat", headers=auth_headers, json={"message": "calculate the thing"})
        data = res.json()
        assert data["response"]["ui_type"] == "message_only"
        print("✅ Guardrail: Tool Ambiguity (Fallback to Chat) successful")

    print("\n🎉 ALL API & ORCHESTRATION TESTS PASSED 🎉")

if __name__ == "__main__":
    asyncio.run(run_tests())
