"""
Metrics - Prometheus-compatible metrics
"""

import time
from typing import Dict, Counter
from dataclasses import dataclass, field


@dataclass
class MetricsCollector:
    """Simple metrics collector"""
    
    # Counters
    requests_total: int = 0
    requests_by_status: Dict[int, int] = field(default_factory=dict)
    requests_by_method: Dict[str, int] = field(default_factory=dict)
    
    # Gauges
    active_tunnels: int = 0
    
    # Histogram buckets (simplified)
    request_duration_buckets: Dict[str, int] = field(default_factory=lambda: {
        "<10ms": 0,
        "<50ms": 0,
        "<100ms": 0,
        "<500ms": 0,
        "<1s": 0,
        ">1s": 0
    })
    
    def record_request(self, method: str, status_code: int, duration_ms: float):
        """Record a request"""
        self.requests_total += 1
        
        # By status code
        self.requests_by_status[status_code] = self.requests_by_status.get(status_code, 0) + 1
        
        # By method
        self.requests_by_method[method] = self.requests_by_method.get(method, 0) + 1
        
        # Duration bucket
        if duration_ms < 10:
            self.request_duration_buckets["<10ms"] += 1
        elif duration_ms < 50:
            self.request_duration_buckets["<50ms"] += 1
        elif duration_ms < 100:
            self.request_duration_buckets["<100ms"] += 1
        elif duration_ms < 500:
            self.request_duration_buckets["<500ms"] += 1
        elif duration_ms < 1000:
            self.request_duration_buckets["<1s"] += 1
        else:
            self.request_duration_buckets[">1s"] += 1
    
    def set_active_tunnels(self, count: int):
        """Set active tunnels count"""
        self.active_tunnels = count
    
    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Requests total
        lines.append("# HELP tunnel_requests_total Total requests")
        lines.append("# TYPE tunnel_requests_total counter")
        lines.append(f"tunnel_requests_total {self.requests_total}")
        
        # Requests by status
        lines.append("# HELP tunnel_requests_by_status Requests by status code")
        lines.append("# TYPE tunnel_requests_by_status counter")
        for status, count in self.requests_by_status.items():
            lines.append(f'tunnel_requests_by_status{{status="{status}"}} {count}')
        
        # Requests by method
        lines.append("# HELP tunnel_requests_by_method Requests by HTTP method")
        lines.append("# TYPE tunnel_requests_by_method counter")
        for method, count in self.requests_by_method.items():
            lines.append(f'tunnel_requests_by_method{{method="{method}"}} {count}')
        
        # Active tunnels
        lines.append("# HELP tunnel_active_tunnels Number of active tunnels")
        lines.append("# TYPE tunnel_active_tunnels gauge")
        lines.append(f"tunnel_active_tunnels {self.active_tunnels}")
        
        # Duration buckets
        lines.append("# HELP tunnel_request_duration_bucket Request duration buckets")
        lines.append("# TYPE tunnel_request_duration_bucket counter")
        for bucket, count in self.request_duration_buckets.items():
            lines.append(f'tunnel_request_duration_bucket{{le="{bucket}"}} {count}')
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """Export metrics as dictionary"""
        return {
            "requests_total": self.requests_total,
            "requests_by_status": self.requests_by_status,
            "requests_by_method": self.requests_by_method,
            "active_tunnels": self.active_tunnels,
            "request_duration_buckets": self.request_duration_buckets
        }


# Global metrics collector
metrics = MetricsCollector()
