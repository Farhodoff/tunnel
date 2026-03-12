"""
Webhook Tester - Test and debug webhooks
"""

import time
import json
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse

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
    
    def __init__(self, max_entries: int = 100):
        self.max_entries = max_entries
        self._entries: Dict[str, List[WebhookRequest]] = {}  # endpoint_id -> requests
    
    def create_endpoint(self) -> str:
        """Create new webhook endpoint"""
        endpoint_id = str(uuid.uuid4())[:8]
        self._entries[endpoint_id] = []
        return endpoint_id
    
    def capture(self, endpoint_id: str, request: WebhookRequest):
        """Capture a webhook request"""
        if endpoint_id not in self._entries:
            self._entries[endpoint_id] = []
        
        self._entries[endpoint_id].append(request)
        
        # Trim old entries
        if len(self._entries[endpoint_id]) > self.max_entries:
            self._entries[endpoint_id] = self._entries[endpoint_id][-self.max_entries:]
    
    def get_requests(self, endpoint_id: str, limit: int = 50) -> List[Dict]:
        """Get captured requests for endpoint"""
        if endpoint_id not in self._entries:
            return []
        
        return [r.to_dict() for r in self._entries[endpoint_id][-limit:]]
    
    def clear(self, endpoint_id: str):
        """Clear requests for endpoint"""
        if endpoint_id in self._entries:
            self._entries[endpoint_id] = []
    
    def delete_endpoint(self, endpoint_id: str):
        """Delete endpoint"""
        if endpoint_id in self._entries:
            del self._entries[endpoint_id]


# Global webhook store
webhook_store = WebhookStore()


@router.post("/create")
async def create_webhook_endpoint():
    """Create new webhook testing endpoint"""
    endpoint_id = webhook_store.create_endpoint()
    return {
        "endpoint_id": endpoint_id,
        "url": f"/webhooks/capture/{endpoint_id}",
        "full_url": f"https://your-domain.com/webhooks/capture/{endpoint_id}"
    }


@router.api_route("/capture/{endpoint_id}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def capture_webhook(
    endpoint_id: str,
    request: Request,
    user_agent: Optional[str] = Header(None)
):
    """Capture webhook request"""
    # Read body
    body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            body = body_bytes.decode("utf-8", errors="ignore")
    except:
        pass
    
    # Create webhook request
    webhook_req = WebhookRequest(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.utcnow().isoformat(),
        method=request.method,
        path=str(request.url),
        headers=dict(request.headers),
        body=body,
        query_params=dict(request.query_params)
    )
    
    # Store it
    webhook_store.capture(endpoint_id, webhook_req)
    
    return JSONResponse(
        content={"status": "captured", "id": webhook_req.id},
        status_code=200
    )


@router.get("/requests/{endpoint_id}")
async def get_webhook_requests(endpoint_id: str, limit: int = 50):
    """Get captured webhook requests"""
    requests = webhook_store.get_requests(endpoint_id, limit)
    return {
        "endpoint_id": endpoint_id,
        "requests": requests,
        "count": len(requests)
    }


@router.delete("/requests/{endpoint_id}")
async def clear_webhook_requests(endpoint_id: str):
    """Clear captured requests"""
    webhook_store.clear(endpoint_id)
    return {"status": "cleared"}


@router.delete("/endpoints/{endpoint_id}")
async def delete_webhook_endpoint(endpoint_id: str):
    """Delete webhook endpoint"""
    webhook_store.delete_endpoint(endpoint_id)
    return {"status": "deleted"}
