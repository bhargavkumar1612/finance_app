from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import accounts, admin, assets, auth, chat, hints, import_api, liabilities, persona, recurring_bills, transactions
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: DB/Redis checks can go here
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Finance Copilot",
    description="AI-powered personal finance chat (India-focused)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server (Phase 3) and same-origin prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/v1", tags=["auth"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])
app.include_router(accounts.router, prefix="/v1", tags=["accounts"])
app.include_router(assets.router, prefix="/v1", tags=["assets"])
app.include_router(liabilities.router, prefix="/v1", tags=["liabilities"])
app.include_router(transactions.router, prefix="/v1", tags=["transactions"])
app.include_router(chat.router, prefix="/v1", tags=["chat"])
app.include_router(import_api.router, prefix="/v1", tags=["import"])
app.include_router(recurring_bills.router, prefix="/v1", tags=["recurring-bills"])
app.include_router(hints.router, prefix="/v1", tags=["hints"])
app.include_router(persona.router, prefix="/v1", tags=["persona"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve legacy static UI at /static-ui (kept for backward compat during dev)
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.is_dir():
    app.mount("/static-ui", StaticFiles(directory=str(static_dir), html=True), name="static")

