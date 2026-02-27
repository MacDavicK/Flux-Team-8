"""Account API endpoints — §17.6"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.middleware.auth import get_current_user
from app.middleware.rate_limit import limiter
from app.models.api_schemas import AccountMeResponse, AccountPatchRequest, PhoneVerifyConfirmRequest, PhoneVerifySendRequest
from app.services.supabase import db
from app.services.twilio_service import confirm_otp, send_otp

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/me", response_model=AccountMeResponse)
@limiter.limit("30/minute")
async def get_me(request: Request, user=Depends(get_current_user)) -> AccountMeResponse:
    """17.6.1"""
    row = await db.fetchrow(
        "SELECT id, email, timezone, onboarded, phone_verified, notification_preferences, monthly_token_usage FROM users WHERE id = $1",
        str(user.id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return AccountMeResponse(
        id=str(row["id"]),
        email=row["email"],
        timezone=row["timezone"],
        onboarded=row["onboarded"],
        phone_verified=row["phone_verified"],
        notification_preferences=row["notification_preferences"],
        monthly_token_usage=row["monthly_token_usage"],
    )


@router.patch("/me")
@limiter.limit("30/minute")
async def patch_me(body: AccountPatchRequest, request: Request, user=Depends(get_current_user)) -> dict:
    """17.6.2"""
    user_id = str(user.id)
    if body.notification_preferences is not None:
        await db.execute(
            "UPDATE users SET notification_preferences = notification_preferences || $2::jsonb WHERE id = $1",
            user_id, json.dumps(body.notification_preferences),
        )
    if body.timezone is not None:
        await db.execute("UPDATE users SET timezone = $2 WHERE id = $1", user_id, body.timezone)
    return {"status": "updated"}


@router.post("/phone/verify/send")
@limiter.limit("3/hour")
async def phone_verify_send(body: PhoneVerifySendRequest, request: Request, user=Depends(get_current_user)) -> dict:
    """17.6.3"""
    user_id = str(user.id)
    await send_otp(body.phone_number)
    await db.execute(
        "UPDATE users SET notification_preferences = notification_preferences || $2::jsonb WHERE id = $1",
        user_id, json.dumps({"phone_number": body.phone_number}),
    )
    return {"status": "sent"}


@router.post("/phone/verify/confirm")
@limiter.limit("30/minute")
async def phone_verify_confirm(body: PhoneVerifyConfirmRequest, request: Request, user=Depends(get_current_user)) -> dict:
    """17.6.4"""
    verified = await confirm_otp(body.phone_number, body.code)
    if verified:
        await db.execute("UPDATE users SET phone_verified = true WHERE id = $1", str(user.id))
        return {"verified": True}
    raise HTTPException(status_code=400, detail="Invalid code")


@router.post("/whatsapp/opt-in")
@limiter.limit("30/minute")
async def whatsapp_opt_in(request: Request, user=Depends(get_current_user)) -> dict:
    """17.6.5"""
    user_id = str(user.id)
    row = await db.fetchrow("SELECT phone_verified FROM users WHERE id = $1", user_id)
    if row is None or not row["phone_verified"]:
        raise HTTPException(status_code=400, detail="Phone number must be verified before opting in to WhatsApp.")
    await db.execute(
        "UPDATE users SET whatsapp_opt_in_at = now(), notification_preferences = notification_preferences || '{\"whatsapp_opted_in\": true}'::jsonb WHERE id = $1",
        user_id,
    )
    return {"opted_in": True}


@router.delete("/", status_code=204)
@limiter.limit("30/minute")
async def delete_account(request: Request, user=Depends(get_current_user)) -> Response:
    """17.6.6 — GDPR erasure: cascade-delete all user data."""
    user_id = str(user.id)
    await db.execute("DELETE FROM notification_log WHERE task_id IN (SELECT id FROM tasks WHERE user_id = $1)", user_id)
    await db.execute("DELETE FROM dispatch_log WHERE task_id IN (SELECT id FROM tasks WHERE user_id = $1)", user_id)
    await db.execute("DELETE FROM tasks WHERE user_id = $1", user_id)
    await db.execute("DELETE FROM goals WHERE user_id = $1", user_id)
    await db.execute("DELETE FROM patterns WHERE user_id = $1", user_id)
    await db.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = $1)", user_id)
    await db.execute("DELETE FROM conversations WHERE user_id = $1", user_id)
    for table in ("checkpoint_blobs", "checkpoints"):
        try:
            await db.execute(f"DELETE FROM {table} WHERE thread_id = $1", user_id)  # noqa: S608
        except Exception:
            pass
    await db.execute("DELETE FROM users WHERE id = $1", user_id)
    return Response(status_code=204)


@router.get("/export")
@limiter.limit("30/minute")
async def export_account(request: Request, user=Depends(get_current_user)) -> dict:
    """17.6.7 — GDPR portability: return all user data as JSON."""
    user_id = str(user.id)

    def _rows(rows) -> list:
        result = []
        for row in rows:
            d = dict(row)
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
                elif not isinstance(v, (str, int, float, bool, dict, list, type(None))):
                    d[k] = str(v)
            result.append(d)
        return result

    user_row = await db.fetchrow("SELECT id, email, timezone, onboarded, phone_verified, whatsapp_opt_in_at, profile, notification_preferences, monthly_token_usage FROM users WHERE id = $1", user_id)
    goals = await db.fetch("SELECT * FROM goals WHERE user_id = $1 ORDER BY created_at", user_id)
    tasks = await db.fetch("SELECT * FROM tasks WHERE user_id = $1 ORDER BY created_at", user_id)
    patterns = await db.fetch("SELECT * FROM patterns WHERE user_id = $1 ORDER BY created_at", user_id)
    conversations = await db.fetch("SELECT * FROM conversations WHERE user_id = $1 ORDER BY created_at", user_id)
    conv_ids = [str(c["id"]) for c in conversations]
    messages = await db.fetch("SELECT * FROM messages WHERE conversation_id = ANY($1::uuid[]) ORDER BY created_at", conv_ids) if conv_ids else []

    user_dict = {}
    if user_row:
        user_dict = dict(user_row)
        for k, v in user_dict.items():
            if hasattr(v, "isoformat"):
                user_dict[k] = v.isoformat()
            elif not isinstance(v, (str, int, float, bool, dict, list, type(None))):
                user_dict[k] = str(v)

    return {
        "user": user_dict,
        "goals": _rows(goals),
        "tasks": _rows(tasks),
        "patterns": _rows(patterns),
        "conversations": _rows(conversations),
        "messages": _rows(messages),
    }
