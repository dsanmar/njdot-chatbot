"""Conversation history endpoints for NJDOT Chatbot.

GET /api/conversations                           → list conversations for the authenticated user
GET /api/conversations/{conversation_id}/messages → messages for a specific conversation

Auth: Supabase JWT must be passed as ``Authorization: Bearer <token>``.
The ``sub`` claim in the decoded token is used as the user ID to scope queries.
"""

from __future__ import annotations

from typing import List

import jwt
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config import config
from app.database import get_db

router = APIRouter(tags=["conversations"])


# ── Auth helper ───────────────────────────────────────────────────────────────

def _user_id_from_token(authorization: str | None) -> str:
    """Decode the Supabase JWT and return the user's UUID (``sub`` claim)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization[7:]

    if not config.SUPABASE_JWT_SECRET:
        # If the JWT secret isn't configured, extract sub without verification.
        # Suitable for local dev only — never do this in production.
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload["sub"]
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Cannot decode token: {exc}") from exc

    try:
        payload = jwt.decode(
            token,
            config.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


# ── Response models ───────────────────────────────────────────────────────────

class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations:  list = []
    bdc_alerts: list = []
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/api/conversations", response_model=List[ConversationOut])
async def list_conversations(
    authorization: str | None = Header(default=None),
) -> list:
    """Return the 40 most-recent conversations for the authenticated user."""
    user_id = _user_id_from_token(authorization)
    db = get_db()
    result = (
        db.table("conversations")
        .select("id, title, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(40)
        .execute()
    )
    return result.data or []


@router.get(
    "/api/conversations/{conversation_id}/messages",
    response_model=List[MessageOut],
)
async def get_conversation_messages(
    conversation_id: str,
    authorization: str | None = Header(default=None),
) -> list:
    """Return all messages for a conversation, verifying it belongs to the user."""
    user_id = _user_id_from_token(authorization)
    db = get_db()

    # Confirm the conversation belongs to this user
    conv = (
        db.table("conversations")
        .select("id")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs = (
        db.table("messages")
        .select("id, role, content, citations, bdc_alerts, created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return msgs.data or []
