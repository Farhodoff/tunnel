"""
Request Logger - Log all HTTP requests
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class RequestLog:
    """Request log entry"""

    request_id: str
    timestamp: str
    method: str
    path: str
    subdomain: str
    client_ip: str
    status_code: int
    duration_ms: float
    user_agent: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None
    body_b64: Optional[str] = None
    request_size: int = 0
    response_size: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


class RequestLogger:
    """Logger for HTTP requests"""

    def __init__(
        self,
        max_entries: int = 1000,
        log_file: Optional[str] = None,
        retention_seconds: Optional[int] = None,
        max_body_bytes: int = 1024 * 1024,
    ):
        self.max_entries = max_entries
        self.log_file = log_file
        self._entries: List[RequestLog] = []
        self._enabled = True
        self.retention_seconds = retention_seconds or int(
            os.getenv("TUNNEL_LOG_RETENTION", "86400")
        )
        self.max_body_bytes = max(0, max_body_bytes)

    def enable(self):
        """Enable logging"""
        self._enabled = True

    def disable(self):
        """Disable logging"""
        self._enabled = False

    def log(
        self,
        method: str,
        path: str,
        subdomain: str,
        client_ip: str,
        status_code: int,
        duration_ms: float,
        user_agent: Optional[str] = None,
        request_id: str = "",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        body_b64: Optional[str] = None,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Log a request"""
        if not self._enabled:
            return

        if body_b64 and len(body_b64) * 3 // 4 > self.max_body_bytes:
            body = None
            body_b64 = None
        entry = RequestLog(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
            method=method,
            path=path,
            subdomain=subdomain,
            client_ip=client_ip,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            user_agent=user_agent,
            headers=dict(headers or {}),
            body=body,
            body_b64=body_b64,
            request_size=request_size,
            response_size=response_size,
        )

        self._entries.append(entry)
        self._purge_expired()

        # Trim old entries
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]

        # Write to file if configured
        if self.log_file:
            self._write_to_file(entry)

    def _purge_expired(self):
        cutoff = time.time() - self.retention_seconds
        self._entries = [
            entry
            for entry in self._entries
            if datetime.fromisoformat(entry.timestamp).timestamp() >= cutoff
        ]

    def _write_to_file(self, entry: RequestLog):
        """Write entry to log file"""
        if not self.log_file:
            return
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            print(f"[RequestLogger] Failed to write to file: {e}")

    def get_entries(
        self,
        limit: int = 100,
        subdomain: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        path: Optional[str] = None,
        since: Optional[float] = None,
        offset: int = 0,
    ) -> List[Dict]:
        """Get log entries"""
        self._purge_expired()
        entries = self._entries

        if subdomain:
            entries = [e for e in entries if e.subdomain == subdomain]
        if method:
            entries = [e for e in entries if e.method.upper() == method.upper()]
        if status_code is not None:
            entries = [e for e in entries if e.status_code == status_code]
        if path:
            entries = [e for e in entries if path.lower() in e.path.lower()]
        if since is not None:
            cutoff = datetime.utcnow().timestamp() - since
            entries = [
                e
                for e in entries
                if datetime.fromisoformat(e.timestamp).timestamp() >= cutoff
            ]

        start = max(0, len(entries) - offset - limit)
        end = len(entries) - offset if offset else len(entries)
        return [e.to_dict() for e in entries[start:end]]

    def get_entry(self, request_id: str) -> Optional[Dict]:
        """Get one request log entry by its tunnel request ID."""
        for entry in reversed(self._entries):
            if entry.request_id == request_id:
                return entry.to_dict()
        return None

    def get_stats(self) -> Dict:
        """Get request statistics"""
        if not self._entries:
            return {"total_requests": 0, "avg_duration_ms": 0, "status_codes": {}}

        status_codes: Dict[int, int] = {}
        total_duration: float = 0

        for entry in self._entries:
            status_codes[entry.status_code] = status_codes.get(entry.status_code, 0) + 1
            total_duration += entry.duration_ms

        return {
            "total_requests": len(self._entries),
            "avg_duration_ms": round(total_duration / len(self._entries), 2),
            "status_codes": status_codes,
            "request_bytes": sum(e.request_size for e in self._entries),
            "response_bytes": sum(e.response_size for e in self._entries),
        }

    def get_stats_for(self, **filters) -> Dict:
        """Return statistics for the same filters accepted by get_entries."""
        entries = self.get_entries(limit=self.max_entries, **filters)
        if not entries:
            return {
                "total_requests": 0,
                "avg_duration_ms": 0,
                "status_codes": {},
                "request_bytes": 0,
                "response_bytes": 0,
            }
        statuses: Dict[int, int] = {}
        for entry in entries:
            statuses[entry["status_code"]] = statuses.get(entry["status_code"], 0) + 1
        return {
            "total_requests": len(entries),
            "avg_duration_ms": round(
                sum(e["duration_ms"] for e in entries) / len(entries), 2
            ),
            "status_codes": statuses,
            "request_bytes": sum(e["request_size"] for e in entries),
            "response_bytes": sum(e["response_size"] for e in entries),
        }

    def clear(self):
        """Clear all entries"""
        self._entries = []


# Global request logger
request_logger = RequestLogger(max_entries=1000)
