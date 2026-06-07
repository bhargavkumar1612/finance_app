"""Post-session persona hook — rules merge + optional LLM delta (S2.6)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_client import LLMProvider, chat_complete, get_llm_provider
from app.services.persona_rules import derive_category_skew
from app.services.persona_store import get_persona, upsert_persona

_RULES_TRAIT_KEYS = frozenset({"top_category", "top_category_pct", "subscription_heavy"})


def _rules_traits_from_skew(skew: dict) -> dict:
    traits: dict = {}
    if skew.get("top_category"):
        traits["top_category"] = skew["top_category"]
    if skew.get("top_category_pct"):
        traits["top_category_pct"] = skew["top_category_pct"]
    if skew.get("subscription_heavy"):
        traits["subscription_heavy"] = True
    return traits


def _merge_traits(existing: dict, llm_traits: dict, rules_traits: dict) -> dict:
    merged = {**(existing or {})}
    merged.update(llm_traits or {})
    for key, value in (rules_traits or {}).items():
        if key in _RULES_TRAIT_KEYS or value is not None:
            merged[key] = value
    return merged


def _parse_llm_persona_response(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    notes = data.get("notes")
    traits = data.get("traits")
    if notes is None and not isinstance(traits, dict):
        return None
    return {
        "notes": str(notes).strip() if notes else "",
        "traits": traits if isinstance(traits, dict) else {},
    }


def _append_body_delta(existing_body: str, notes: str) -> str:
    if not notes:
        return existing_body
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    block = f"---\n{stamp}: {notes}"
    base = (existing_body or "").strip()
    return f"{base}\n\n{block}" if base else block


def _build_llm_messages(history: list[dict], existing_body: str) -> list[dict]:
    recent = history[-6:] if history else []
    convo = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}"
        for m in recent
        if m.get("content")
    )
    system = (
        "You summarize a user's financial persona from chat. "
        "Return ONLY JSON: {\"notes\": \"short paragraph\", \"traits\": {\"key\": \"value\"}}. "
        "Traits are optional hints (e.g. goals, risk_tone). Do not invent account balances."
    )
    user = (
        f"Existing persona notes:\n{existing_body or '(empty)'}\n\n"
        f"Recent conversation:\n{convo or '(no history)'}\n\n"
        "Update notes with anything new from this session."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def run_persona_hook(
    session: AsyncSession,
    user_id: UUID,
    history: list[dict],
) -> None:
    """Derive rules traits and optionally merge an LLM delta into stored persona."""
    skew = await derive_category_skew(session, user_id)
    rules_traits = _rules_traits_from_skew(skew)
    current = await get_persona(session, user_id)
    merged_traits = _merge_traits(current.get("traits") or {}, {}, rules_traits)
    merged_body = current.get("body") or ""

    await upsert_persona(session, user_id, body=merged_body, traits=merged_traits)

    if get_llm_provider() == LLMProvider.none:
        return

    llm_text = chat_complete(_build_llm_messages(history, merged_body), temperature=0.2, max_tokens=512)
    if not llm_text:
        return

    parsed = _parse_llm_persona_response(llm_text)
    if not parsed:
        return

    merged_body = _append_body_delta(merged_body, parsed.get("notes", ""))
    merged_traits = _merge_traits(merged_traits, parsed.get("traits") or {}, rules_traits)
    await upsert_persona(session, user_id, body=merged_body, traits=merged_traits)
