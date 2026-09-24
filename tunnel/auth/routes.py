"""Auth REST API - API key management.

Bootstrap: if auth is disabled (no keys yet), endpoints are open so the
first key can be created. Once any key exists, a valid key is required
via `X-API-Key` header or `Authorization: Bearer <key>`.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from tunnel.auth.manager import auth_manager


router = APIRouter(prefix="/api/keys", tags=["auth"])


class CreateKeyBody(BaseModel):
    name: str = "default"
    expires_in_days: Optional[int] = None


def _extract_token(
    x_api_key: Optional[str], authorization: Optional[str]
) -> Optional[str]:
    if x_api_key:
        return x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def require_admin(
    x_api_key: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
):
    """Allow bootstrap when disabled; otherwise require a valid key."""
    if not auth_manager.is_enabled:
        return
    token = _extract_token(x_api_key, authorization)
    if not token or not auth_manager.validate_key(token):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.get("", dependencies=[Depends(require_admin)])
async def list_keys():
    return {"enabled": auth_manager.is_enabled, "keys": auth_manager.list_keys()}


@router.post("", dependencies=[Depends(require_admin)])
async def create_key(body: CreateKeyBody):
    raw = auth_manager.generate_key(body.name, body.expires_in_days)
    info = auth_manager.get_key_info(raw)
    return {
        "key_id": info.key_id if info else None,
        "api_key": raw,  # shown ONCE - store it now
        "name": body.name,
        "expires_in_days": body.expires_in_days,
    }


@router.delete("/{key_id}", dependencies=[Depends(require_admin)])
async def revoke_key(key_id: str):
    if not auth_manager.revoke_key(key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    return {"status": "revoked", "key_id": key_id}
