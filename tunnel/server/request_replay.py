"""
Request logging and replay functionality
Similar to webhook.site - capture and replay HTTP requests
"""

import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class CapturedRequest:
    """Represents a captured HTTP request"""
    id: str
    timestamp: str
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Optional[str]
    client_ip: str
    subdomain: str
    
    @classmethod
    def capture(cls, request_data: Dict[str, Any]) -> 'CapturedRequest':
        """Create a captured request from request data"""
        return cls(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.utcnow().isoformat(),
            method=request_data.get('method', 'GET'),
            path=request_data.get('path', '/'),
            headers=request_data.get('headers', {}),
            query_params=request_data.get('query_params', {}),
            body=request_data.get('body'),
            client_ip=request_data.get('client_ip', 'unknown'),
            subdomain=request_data.get('subdomain', 'default')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class RequestReplayManager:
    """Manages request capture and replay functionality"""
    
    def __init__(self, max_requests: int = 1000):
        self.captured_requests: Dict[str, List[CapturedRequest]] = {}
        self.max_requests = max_requests
        self.replay_endpoints: Dict[str, Dict[str, Any]] = {}
    
    def create_replay_endpoint(self, subdomain: str, description: str = "") -> str:
        """Create a new replay endpoint"""
        endpoint_id = str(uuid.uuid4())[:8]
        self.replay_endpoints[endpoint_id] = {
            'id': endpoint_id,
            'subdomain': subdomain,
            'description': description,
            'created_at': datetime.utcnow().isoformat(),
            'request_count': 0
        }
        self.captured_requests[endpoint_id] = []
        return endpoint_id
    
    def capture_request(self, endpoint_id: str, request_data: Dict[str, Any]) -> Optional[CapturedRequest]:
        """Capture a request for an endpoint"""
        if endpoint_id not in self.captured_requests:
            return None
        
        captured = CapturedRequest.capture(request_data)
        self.captured_requests[endpoint_id].append(captured)
        
        # Update request count
        if endpoint_id in self.replay_endpoints:
            self.replay_endpoints[endpoint_id]['request_count'] += 1
        
        # Limit stored requests
        if len(self.captured_requests[endpoint_id]) > self.max_requests:
            self.captured_requests[endpoint_id].pop(0)
        
        return captured
    
    def get_requests(self, endpoint_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get captured requests for an endpoint"""
        if endpoint_id not in self.captured_requests:
            return []
        
        requests = self.captured_requests[endpoint_id]
        return [r.to_dict() for r in reversed(requests[-limit:])]
    
    def get_request(self, endpoint_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific request by ID"""
        if endpoint_id not in self.captured_requests:
            return None
        
        for req in self.captured_requests[endpoint_id]:
            if req.id == request_id:
                return req.to_dict()
        return None
    
    def clear_requests(self, endpoint_id: str) -> bool:
        """Clear all captured requests for an endpoint"""
        if endpoint_id in self.captured_requests:
            self.captured_requests[endpoint_id] = []
            if endpoint_id in self.replay_endpoints:
                self.replay_endpoints[endpoint_id]['request_count'] = 0
            return True
        return False
    
    def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete a replay endpoint"""
        if endpoint_id in self.replay_endpoints:
            del self.replay_endpoints[endpoint_id]
            if endpoint_id in self.captured_requests:
                del self.captured_requests[endpoint_id]
            return True
        return False
    
    def get_endpoint_info(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get endpoint information"""
        return self.replay_endpoints.get(endpoint_id)
    
    def list_endpoints(self, subdomain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all replay endpoints"""
        endpoints = list(self.replay_endpoints.values())
        if subdomain:
            endpoints = [e for e in endpoints if e['subdomain'] == subdomain]
        return endpoints
    
    def replay_request(self, endpoint_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a request for replay"""
        request = self.get_request(endpoint_id, request_id)
        if request:
            return {
                'original_request': request,
                'replay_timestamp': datetime.utcnow().isoformat(),
                'replay_note': 'Use this data to replay the request'
            }
        return None


# Global instance
replay_manager = RequestReplayManager()
