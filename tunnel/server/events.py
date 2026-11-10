import json
import time
from typing import Dict, Any

def create_tunnel_lifecycle_event(event_type: str, tunnel_id: str, subdomain: str, client_ip: str) -> str:
    """Format structured JSON audit event for tunnel open/close lifecycle."""
    payload: Dict[str, Any] = {
        "event": event_type,
        "tunnel_id": tunnel_id,
        "subdomain": subdomain,
        "client_ip": client_ip,
        "timestamp": int(time.time()),
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    return json.dumps(payload)
