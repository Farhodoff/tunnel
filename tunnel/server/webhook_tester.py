"""
Webhook Tester - Test and debug webhooks
"""

import json
import os
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from tunnel.auth.routes import require_admin
from tunnel.utils.rate_limiter import rate_limiter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@dataclass
class WebhookRequest:
    """Captured webhook request"""

    id: str
    timestamp: str
    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[str]
    query_params: Dict[str, str]

    def to_dict(self) -> Dict:
        return asdict(self)


class WebhookStore:
    """Store for captured webhook requests"""

    def __init__(
        self,
        max_entries: int = 100,
        storage_path: Optional[str] = None,
        retention_seconds: int = 86400,
    ):
        self.max_entries = max_entries
        self.storage_path = Path(storage_path) if storage_path else None
        self.retention_seconds = retention_seconds
        self._entries: Dict[str, List[WebhookRequest]] = {}  # endpoint_id -> requests
        self._load()

    def _load(self):
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            raw = json.loads(self.storage_path.read_text())
            cutoff = datetime.utcnow().timestamp() - self.retention_seconds
            self._entries = {
                endpoint_id: [
                    WebhookRequest(**entry)
                    for entry in entries
                    if datetime.fromisoformat(entry["timestamp"]).timestamp() >= cutoff
                ][-self.max_entries :]
                for endpoint_id, entries in raw.items()
            }
        except (OSError, ValueError, TypeError, KeyError):
            self._entries = {}

    def _save(self):
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.storage_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(
                {
                    endpoint_id: [entry.to_dict() for entry in entries]
                    for endpoint_id, entries in self._entries.items()
                }
            )
        )
        temp_path.replace(self.storage_path)

    def create_endpoint(self) -> str:
        """Create new webhook endpoint"""
        endpoint_id = str(uuid.uuid4())[:8]
        self._entries[endpoint_id] = []
        self._save()
        return endpoint_id

    def capture(self, endpoint_id: str, request: WebhookRequest):
        """Capture a webhook request"""
        if endpoint_id not in self._entries:
            self._entries[endpoint_id] = []

        self._entries[endpoint_id].append(request)

        # Trim old entries
        if len(self._entries[endpoint_id]) > self.max_entries:
            self._entries[endpoint_id] = self._entries[endpoint_id][-self.max_entries :]
        self._save()

    def get_requests(self, endpoint_id: str, limit: int = 50) -> List[Dict]:
        """Get captured requests for endpoint"""
        if endpoint_id not in self._entries:
            raise KeyError(endpoint_id)

        return [r.to_dict() for r in self._entries[endpoint_id][-limit:]]

    def clear(self, endpoint_id: str):
        """Clear requests for endpoint"""
        if endpoint_id in self._entries:
            self._entries[endpoint_id] = []
            self._save()

    def delete_endpoint(self, endpoint_id: str):
        """Delete endpoint"""
        if endpoint_id in self._entries:
            del self._entries[endpoint_id]
            self._save()


# Global webhook store
webhook_store = WebhookStore(
    storage_path=os.getenv("TUNNEL_WEBHOOK_STORE") or None,
    retention_seconds=int(os.getenv("TUNNEL_WEBHOOK_RETENTION", "86400")),
)


@router.post("/create", dependencies=[Depends(require_admin)])
async def create_webhook_endpoint():
    """Create new webhook testing endpoint"""
    endpoint_id = webhook_store.create_endpoint()
    return {
        "endpoint_id": endpoint_id,
        "url": f"/webhooks/capture/{endpoint_id}",
        "full_url": f"https://your-domain.com/webhooks/capture/{endpoint_id}",
    }


@router.api_route(
    "/capture/{endpoint_id}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
)
async def capture_webhook(endpoint_id: str, request: Request):
    """Capture webhook request"""
    if endpoint_id not in webhook_store._entries:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(f"webhook:{client_ip}"):
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
    # Read body
    body = None
    body_bytes = await request.body()
    max_body = int(os.getenv("TUNNEL_WEBHOOK_MAX_BODY", str(1024 * 1024)))
    if len(body_bytes) > max_body:
        return JSONResponse(
            status_code=413,
            content={"error": "Webhook body too large", "max_bytes": max_body},
        )
    if body_bytes:
        body = body_bytes.decode("utf-8", errors="ignore")

    # Create webhook request
    webhook_req = WebhookRequest(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.utcnow().isoformat(),
        method=request.method,
        path=str(request.url),
        headers=dict(request.headers),
        body=body,
        query_params=dict(request.query_params),
    )

    # Store it
    webhook_store.capture(endpoint_id, webhook_req)

    return JSONResponse(
        content={"status": "captured", "id": webhook_req.id}, status_code=200
    )


@router.get("/requests/{endpoint_id}", dependencies=[Depends(require_admin)])
async def get_webhook_requests(endpoint_id: str, limit: int = 50):
    """Get captured webhook requests"""
    try:
        requests = webhook_store.get_requests(endpoint_id, max(1, min(limit, 100)))
    except KeyError:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    return {"endpoint_id": endpoint_id, "requests": requests, "count": len(requests)}


@router.delete("/requests/{endpoint_id}", dependencies=[Depends(require_admin)])
async def clear_webhook_requests(endpoint_id: str):
    """Clear captured requests"""
    webhook_store.clear(endpoint_id)
    return {"status": "cleared"}


@router.delete("/endpoints/{endpoint_id}", dependencies=[Depends(require_admin)])
async def delete_webhook_endpoint(endpoint_id: str):
    """Delete webhook endpoint"""
    if endpoint_id not in webhook_store._entries:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    webhook_store.delete_endpoint(endpoint_id)
    return {"status": "deleted"}
