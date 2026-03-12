"""
Traffic inspection and performance monitoring
- HTTP headers inspection
- Latency tracking
- Bandwidth monitoring
"""

import time
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime
import statistics


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    request_id: str
    timestamp: float
    method: str
    path: str
    subdomain: str
    client_ip: str
    
    # Timing
    start_time: float
    end_time: Optional[float] = None
    latency_ms: Optional[float] = None
    
    # Headers
    request_headers: Dict[str, str] = field(default_factory=dict)
    response_headers: Dict[str, str] = field(default_factory=dict)
    
    # Body info
    request_body_size: int = 0
    response_body_size: int = 0
    
    # Status
    status_code: Optional[int] = None
    error: Optional[str] = None
    
    def finish(self, status_code: int, response_headers: Dict[str, str], response_body_size: int):
        """Mark request as finished and calculate metrics"""
        self.end_time = time.time()
        self.status_code = status_code
        self.response_headers = response_headers
        self.response_body_size = response_body_size
        self.latency_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'request_id': self.request_id,
            'timestamp': datetime.fromtimestamp(self.timestamp).isoformat(),
            'method': self.method,
            'path': self.path,
            'subdomain': self.subdomain,
            'client_ip': self.client_ip,
            'latency_ms': round(self.latency_ms, 2) if self.latency_ms else None,
            'status_code': self.status_code,
            'request_headers': self.request_headers,
            'response_headers': self.response_headers,
            'request_body_size': self.request_body_size,
            'response_body_size': self.response_body_size,
            'total_bytes': self.request_body_size + self.response_body_size,
            'error': self.error
        }


class TrafficInspector:
    """Inspect and monitor HTTP traffic"""
    
    def __init__(self, max_requests: int = 1000):
        self.requests: deque = deque(maxlen=max_requests)
        self.active_requests: Dict[str, RequestMetrics] = {}
        
        # Performance stats
        self.total_requests = 0
        self.total_bytes_in = 0
        self.total_bytes_out = 0
        self.latencies: deque = deque(maxlen=1000)
        
        # Status code distribution
        self.status_codes: Dict[int, int] = {}
        
        # Method distribution
        self.methods: Dict[str, int] = {}
    
    def start_request(self, request_id: str, method: str, path: str, 
                      subdomain: str, client_ip: str,
                      headers: Dict[str, str], body_size: int = 0) -> RequestMetrics:
        """Start tracking a request"""
        metrics = RequestMetrics(
            request_id=request_id,
            timestamp=time.time(),
            method=method,
            path=path,
            subdomain=subdomain,
            client_ip=client_ip,
            start_time=time.time(),
            request_headers=dict(headers),
            request_body_size=body_size
        )
        
        self.active_requests[request_id] = metrics
        self.total_requests += 1
        self.total_bytes_in += body_size
        
        # Track method
        self.methods[method] = self.methods.get(method, 0) + 1
        
        return metrics
    
    def finish_request(self, request_id: str, status_code: int,
                       response_headers: Dict[str, str], response_body_size: int):
        """Finish tracking a request"""
        if request_id not in self.active_requests:
            return
        
        metrics = self.active_requests.pop(request_id)
        metrics.finish(status_code, dict(response_headers), response_body_size)
        
        # Store completed request
        self.requests.append(metrics)
        
        # Update stats
        self.total_bytes_out += response_body_size
        self.latencies.append(metrics.latency_ms)
        
        # Track status code
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
    
    def get_recent_requests(self, limit: int = 50, subdomain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent requests with optional filtering"""
        requests_list = list(self.requests)
        if subdomain:
            requests_list = [r for r in requests_list if r.subdomain == subdomain]
        
        return [r.to_dict() for r in reversed(requests_list[-limit:])]
    
    def get_request_details(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific request"""
        # Check active requests
        if request_id in self.active_requests:
            return self.active_requests[request_id].to_dict()
        
        # Check completed requests
        for req in self.requests:
            if req.request_id == request_id:
                return req.to_dict()
        
        return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {
            'total_requests': self.total_requests,
            'active_requests': len(self.active_requests),
            'total_bytes_in': self.total_bytes_in,
            'total_bytes_out': self.total_bytes_out,
            'total_bytes': self.total_bytes_in + self.total_bytes_out,
            'status_codes': self.status_codes,
            'methods': self.methods
        }
        
        # Latency statistics
        if self.latencies:
            latencies_list = list(self.latencies)
            stats['latency'] = {
                'avg_ms': round(statistics.mean(latencies_list), 2),
                'min_ms': round(min(latencies_list), 2),
                'max_ms': round(max(latencies_list), 2),
                'p50_ms': round(statistics.median(latencies_list), 2),
                'p95_ms': round(self._percentile(latencies_list, 95), 2),
                'p99_ms': round(self._percentile(latencies_list, 99), 2)
            }
        else:
            stats['latency'] = None
        
        return stats
    
    def get_bandwidth_stats(self, time_window_seconds: int = 60) -> Dict[str, Any]:
        """Get bandwidth statistics for a time window"""
        cutoff_time = time.time() - time_window_seconds
        
        recent_requests = [r for r in self.requests if r.timestamp >= cutoff_time]
        
        bytes_in = sum(r.request_body_size for r in recent_requests)
        bytes_out = sum(r.response_body_size for r in recent_requests)
        
        return {
            'time_window_seconds': time_window_seconds,
            'requests_count': len(recent_requests),
            'bytes_in': bytes_in,
            'bytes_out': bytes_out,
            'total_bytes': bytes_in + bytes_out,
            'bytes_in_per_second': round(bytes_in / time_window_seconds, 2),
            'bytes_out_per_second': round(bytes_out / time_window_seconds, 2)
        }
    
    def inspect_headers(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Inspect headers for a specific request"""
        details = self.get_request_details(request_id)
        if not details:
            return None
        
        return {
            'request_id': request_id,
            'request_headers': details.get('request_headers', {}),
            'response_headers': details.get('response_headers', {}),
            'security_headers': self._analyze_security_headers(
                details.get('response_headers', {})
            )
        }
    
    def _analyze_security_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Analyze security headers in response"""
        security_headers = {
            'Strict-Transport-Security': 'HSTS',
            'X-Content-Type-Options': 'Content-Type protection',
            'X-Frame-Options': 'Clickjacking protection',
            'X-XSS-Protection': 'XSS protection',
            'Content-Security-Policy': 'CSP',
            'Referrer-Policy': 'Referrer policy'
        }
        
        analysis = {}
        for header, description in security_headers.items():
            header_lower = header.lower()
            found = any(k.lower() == header_lower for k in headers.keys())
            analysis[header] = {
                'present': found,
                'description': description,
                'value': next((v for k, v in headers.items() 
                              if k.lower() == header_lower), None)
            }
        
        return analysis
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def clear(self):
        """Clear all data"""
        self.requests.clear()
        self.active_requests.clear()
        self.latencies.clear()
        self.status_codes.clear()
        self.methods.clear()
        self.total_requests = 0
        self.total_bytes_in = 0
        self.total_bytes_out = 0


# Global instance
traffic_inspector = TrafficInspector()
