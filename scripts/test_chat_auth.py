import asyncio
import httpx

async def test_api():
    base_url = "http://localhost:8000/v1"
    
    async with httpx.AsyncClient() as client:
        # 1. Login
        print("\n--- 1. Login ---")
        res = await client.post(f"{base_url}/login", json={"email": "tester@local"})
        print(f"Status: {res.status_code}")
        user = res.json()
        print(user)
        
        headers = {"X-User-Email": user["email"]}
        
        # 2. Chat (new session)
        print("\n--- 2. Chat (New) ---")
        res = await client.post(f"{base_url}/chat", headers=headers, json={"message": "hello"})
        print(f"Status: {res.status_code}")
        chat_data = res.json()
        print(chat_data)
        
        session_id = chat_data["conversation_id"]
        
        # 3. Chat (existing session)
        print("\n--- 3. Chat (Followup) ---")
        res = await client.post(f"{base_url}/chat", headers=headers, json={"message": "how are you?", "conversation_id": session_id})
        print(f"Status: {res.status_code}")
        
        # 4. List Sessions
        print("\n--- 4. List Sessions ---")
        res = await client.get(f"{base_url}/chat/sessions", headers=headers)
        print(f"Status: {res.status_code}")
        print(res.json())
        
        # 5. List Messages
        print("\n--- 5. List Messages ---")
        res = await client.get(f"{base_url}/chat/sessions/{session_id}", headers=headers)
        print(f"Status: {res.status_code}")
        msgs = res.json()
        for m in msgs:
            print(f"[{m['role']}] {m['text'][:50]}")

if __name__ == "__main__":
    asyncio.run(test_api())
