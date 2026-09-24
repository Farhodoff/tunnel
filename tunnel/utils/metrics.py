"""
Metrics - Prometheus metrics via prometheus_client (manual fallback if missing)
"""

import time
from typing import Dict
from dataclasses import dataclass, field

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _PROM_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback path
    _PROM_AVAILABLE = False

# Standard latency buckets (seconds) for proxied requests
DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


@dataclass
class MetricsCollector:
    """Prometheus metrics collector (same public API as before)"""

    # Plain counters (also used for to_dict + manual fallback)
    requests_total: int = 0
    requests_by_status: Dict[int, int] = field(default_factory=dict)
    requests_by_method: Dict[str, int] = field(default_factory=dict)

    # Gauges
    active_tunnels: int = 0

    def __post_init__(self):
        self._registry = None
        self._counter = None
        self._histogram = None
        self._gauge = None
        if _PROM_AVAILABLE:
            # Private registry: reload-safe (no global dup registration)
            self._registry = CollectorRegistry()
            self._counter = Counter(
                "tunnel_requests_total",
                "Total proxied requests",
                ["method", "status"],
                registry=self._registry,
            )
            self._histogram = Histogram(
                "tunnel_request_duration_seconds",
                "Proxied request latency",
                ["method"],
                registry=self._registry,
                buckets=DURATION_BUCKETS,
            )
            self._gauge = Gauge(
                "tunnel_active_tunnels",
                "Number of active tunnels",
                registry=self._registry,
            )

    @property
    def use_prom(self) -> bool:
        return self._registry is not None

    def record_request(self, method: str, status_code: int, duration_ms: float):
        """Record a request"""
        method = method or "UNKNOWN"
        self.requests_total += 1
        self.requests_by_status[status_code] = (
            self.requests_by_status.get(status_code, 0) + 1
        )
        self.requests_by_method[method] = self.requests_by_method.get(method, 0) + 1
        if self.use_prom:
            self._counter.labels(method=method, status=str(status_code)).inc()
            self._histogram.labels(method=method).observe(
                max(0.0, duration_ms) / 1000.0
            )

    def set_active_tunnels(self, count: int):
        """Set active tunnels count"""
        self.active_tunnels = count
        if self.use_prom:
            self._gauge.set(count)

    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        if self.use_prom:
            return generate_latest(self._registry).decode("utf-8")
        # Manual fallback (identical shape to previous implementation)
        lines = [
            "# HELP tunnel_requests_total Total requests",
            "# TYPE tunnel_requests_total counter",
            f"tunnel_requests_total {self.requests_total}",
            "# HELP tunnel_requests_by_status Requests by status code",
            "# TYPE tunnel_requests_by_status counter",
        ]
        for status, count in self.requests_by_status.items():
            lines.append(f'tunnel_requests_by_status{{status="{status}"}} {count}')
        lines += [
            "# HELP tunnel_requests_by_method Requests by HTTP method",
            "# TYPE tunnel_requests_by_method counter",
        ]
        for method, count in self.requests_by_method.items():
            lines.append(f'tunnel_requests_by_method{{method="{method}"}} {count}')
        lines += [
            "# HELP tunnel_active_tunnels Number of active tunnels",
            "# TYPE tunnel_active_tunnels gauge",
            f"tunnel_active_tunnels {self.active_tunnels}",
        ]
        return "\n".join(lines) + "\n"

    def to_dict(self) -> Dict:
        """Export metrics as dictionary"""
        return {
            "requests_total": self.requests_total,
            "requests_by_status": self.requests_by_status,
            "requests_by_method": self.requests_by_method,
            "active_tunnels": self.active_tunnels,
        }


# Global metrics collector
metrics = MetricsCollector()
