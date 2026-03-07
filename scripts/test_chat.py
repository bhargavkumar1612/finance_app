import asyncio
from app.agents.planner import plan

async def test():
    print("Test 1: Transaction")
    res1 = await plan("I bought a coffee for $5")
    print("Intent:", res1.intent)
    print("Message:", res1.message)
    print("Steps:", [s.model_dump() for s in res1.steps])
    print("-" * 20)
    print("Test 2: General Chat")
    res2 = await plan("Hi, I want some financial advice")
    print("Intent:", res2.intent)
    print("Message:", res2.message)
    print("Steps:", [s.model_dump() for s in res2.steps])

if __name__ == "__main__":
    asyncio.run(test())
