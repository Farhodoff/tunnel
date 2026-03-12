"""
Request Logger - Log all HTTP requests
"""

import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class RequestLog:
    """Request log entry"""
    timestamp: str
    method: str
    path: str
    subdomain: str
    client_ip: str
    status_code: int
    duration_ms: float
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class RequestLogger:
    """Logger for HTTP requests"""
    
    def __init__(self, max_entries: int = 1000, log_file: Optional[str] = None):
        self.max_entries = max_entries
        self.log_file = log_file
        self._entries: List[RequestLog] = []
        self._enabled = True
    
    def enable(self):
        """Enable logging"""
        self._enabled = True
    
    def disable(self):
        """Disable logging"""
        self._enabled = False
    
    def log(self, method: str, path: str, subdomain: str, 
            client_ip: str, status_code: int, duration_ms: float,
            user_agent: Optional[str] = None):
        """Log a request"""
        if not self._enabled:
            return
        
        entry = RequestLog(
            timestamp=datetime.utcnow().isoformat(),
            method=method,
            path=path,
            subdomain=subdomain,
            client_ip=client_ip,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            user_agent=user_agent
        )
        
        self._entries.append(entry)
        
        # Trim old entries
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]
        
        # Write to file if configured
        if self.log_file:
            self._write_to_file(entry)
    
    def _write_to_file(self, entry: RequestLog):
        """Write entry to log file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(entry.to_dict()) + '\n')
        except Exception as e:
            print(f"[RequestLogger] Failed to write to file: {e}")
    
    def get_entries(self, limit: int = 100, 
                   subdomain: Optional[str] = None) -> List[Dict]:
        """Get log entries"""
        entries = self._entries
        
        if subdomain:
            entries = [e for e in entries if e.subdomain == subdomain]
        
        return [e.to_dict() for e in entries[-limit:]]
    
    def get_stats(self) -> Dict:
        """Get request statistics"""
        if not self._entries:
            return {
                "total_requests": 0,
                "avg_duration_ms": 0,
                "status_codes": {}
            }
        
        status_codes = {}
        total_duration = 0
        
        for entry in self._entries:
            status_codes[entry.status_code] = status_codes.get(entry.status_code, 0) + 1
            total_duration += entry.duration_ms
        
        return {
            "total_requests": len(self._entries),
            "avg_duration_ms": round(total_duration / len(self._entries), 2),
            "status_codes": status_codes
        }
    
    def clear(self):
        """Clear all entries"""
        self._entries = []


# Global request logger
request_logger = RequestLogger(max_entries=1000)
