import asyncio
from app.agents.planner import plan

async def test():
    res = await plan("I bought a coffee for $5")
    print("Intent:", res.intent)
    print("Steps:", [s.model_dump() for s in res.steps])

if __name__ == "__main__":
    asyncio.run(test())
