import time
from typing import Dict, Any

_START_TIME = time.time()

def get_liveness_status() -> Dict[str, Any]:
    return {
        "status": "alive",
        "uptime_seconds": int(time.time() - _START_TIME)
    }

def get_readiness_status(active_tunnels: int, redis_ok: bool = True) -> Dict[str, Any]:
    return {
        "status": "ready" if redis_ok else "degraded",
        "active_tunnels": active_tunnels,
        "redis_healthy": redis_ok
    }
