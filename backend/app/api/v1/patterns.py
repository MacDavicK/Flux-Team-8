"""Patterns API endpoints — §17.5"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.middleware.auth import get_current_user
from app.middleware.rate_limit import limiter
from app.models.api_schemas import PatternPatchRequest
from app.services.supabase import db

router = APIRouter(prefix="/patterns", tags=["patterns"])


@router.get("/")
@limiter.limit("30/minute")
async def list_patterns(request: Request, user=Depends(get_current_user)) -> list:
    """17.5.1"""
    rows = await db.fetch("SELECT id, pattern_type, description, data, confidence, created_at, updated_at FROM patterns WHERE user_id = $1 ORDER BY updated_at DESC", str(user.id))
    return [_s(r) for r in rows]


@router.get("/{pattern_id}")
@limiter.limit("30/minute")
async def get_pattern(pattern_id: str, request: Request, user=Depends(get_current_user)) -> dict:
    """17.5.2"""
    row = await db.fetchrow("SELECT id, pattern_type, description, data, confidence, created_at, updated_at FROM patterns WHERE id = $1 AND user_id = $2", pattern_id, str(user.id))
    if row is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return _s(row)


@router.patch("/{pattern_id}")
@limiter.limit("30/minute")
async def patch_pattern(pattern_id: str, body: PatternPatchRequest, request: Request, user=Depends(get_current_user)) -> dict:
    """17.5.3 — Set data.user_overridden=true when user_override is provided."""
    user_id = str(user.id)
    existing = await db.fetchrow("SELECT id, description, confidence FROM patterns WHERE id = $1 AND user_id = $2", pattern_id, user_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    new_desc = body.description if body.description is not None else existing["description"]
    new_conf = body.confidence if body.confidence is not None else existing["confidence"]
    if body.user_override is not None:
        override_json = json.dumps({**body.user_override, "user_overridden": True})
        row = await db.fetchrow(
            "UPDATE patterns SET data = data || $3::jsonb, description = $4, confidence = $5, updated_at = now() WHERE id = $1 AND user_id = $2 RETURNING id, pattern_type, description, data, confidence, created_at, updated_at",
            pattern_id, user_id, override_json, new_desc, new_conf,
        )
    else:
        row = await db.fetchrow(
            "UPDATE patterns SET description = $3, confidence = $4, updated_at = now() WHERE id = $1 AND user_id = $2 RETURNING id, pattern_type, description, data, confidence, created_at, updated_at",
            pattern_id, user_id, new_desc, new_conf,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return _s(row)


@router.delete("/{pattern_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_pattern(pattern_id: str, request: Request, user=Depends(get_current_user)) -> Response:
    """17.5.4 — Hard delete; return HTTP 204."""
    result = await db.execute("DELETE FROM patterns WHERE id = $1 AND user_id = $2", pattern_id, str(user.id))
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Pattern not found")
    return Response(status_code=204)


def _s(row) -> dict:
    d = dict(row)
    if d.get("id") is not None:
        d["id"] = str(d["id"])
    for k in ("created_at", "updated_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d
