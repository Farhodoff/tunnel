"""
Middleware - Request/Response modification
"""

import re
from typing import Dict, Optional, Callable, List
from dataclasses import dataclass


@dataclass
class RewriteRule:
    """URL rewrite rule"""
    pattern: str
    replacement: str
    method: Optional[str] = None
    
    def apply(self, path: str, method: str) -> Optional[str]:
        """Apply rewrite rule"""
        if self.method and self.method != method:
            return None
        
        if re.match(self.pattern, path):
            return re.sub(self.pattern, self.replacement, path)
        return None


class RequestModifier:
    """Modify requests before forwarding"""
    
    def __init__(self):
        self._header_additions: Dict[str, str] = {}
        self._header_removals: List[str] = []
        self._rewrite_rules: List[RewriteRule] = []
        self._body_transformers: List[Callable] = []
    
    def add_header(self, name: str, value: str):
        """Add header to all requests"""
        self._header_additions[name] = value
    
    def remove_header(self, name: str):
        """Remove header from all requests"""
        self._header_removals.append(name.lower())
    
    def add_rewrite_rule(self, pattern: str, replacement: str, method: Optional[str] = None):
        """Add URL rewrite rule"""
        self._rewrite_rules.append(RewriteRule(pattern, replacement, method))
    
    def modify_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Modify headers"""
        # Remove headers
        for name in self._header_removals:
            headers = {k: v for k, v in headers.items() if k.lower() != name}
        
        # Add headers
        headers.update(self._header_additions)
        
        return headers
    
    def rewrite_path(self, path: str, method: str) -> str:
        """Rewrite path if matching rule found"""
        for rule in self._rewrite_rules:
            new_path = rule.apply(path, method)
            if new_path:
                return new_path
        return path


class ResponseModifier:
    """Modify responses before returning to client"""
    
    def __init__(self):
        self._header_additions: Dict[str, str] = {}
        self._cors_enabled = False
        self._cors_origins = ["*"]
        self._cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self._cors_headers = ["*"]
    
    def add_header(self, name: str, value: str):
        """Add header to all responses"""
        self._header_additions[name] = value
    
    def enable_cors(self, origins: Optional[List[str]] = None, 
                   methods: Optional[List[str]] = None,
                   headers: Optional[List[str]] = None):
        """Enable CORS headers"""
        self._cors_enabled = True
        if origins:
            self._cors_origins = origins
        if methods:
            self._cors_methods = methods
        if headers:
            self._cors_headers = headers
    
    def modify_headers(self, headers: Dict[str, str], request_origin: Optional[str] = None) -> Dict[str, str]:
        """Modify response headers"""
        # Add custom headers
        headers.update(self._header_additions)
        
        # Add CORS headers if enabled
        if self._cors_enabled:
            headers["Access-Control-Allow-Origin"] = ", ".join(self._cors_origins)
            headers["Access-Control-Allow-Methods"] = ", ".join(self._cors_methods)
            headers["Access-Control-Allow-Headers"] = ", ".join(self._cors_headers)
        
        # Security headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["X-XSS-Protection"] = "1; mode=block"
        
        return headers


# Global modifiers
request_modifier = RequestModifier()
response_modifier = ResponseModifier()

# Enable CORS by default
response_modifier.enable_cors()
