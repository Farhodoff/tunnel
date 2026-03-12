"""
Authentication Manager - API key management
"""

import secrets
import hashlib
import time
from typing import Dict, Optional, Set
from dataclasses import dataclass, field


@dataclass
class APIKey:
    """API key data"""
    key_id: str
    key_hash: str
    name: str
    created_at: float
    expires_at: Optional[float] = None
    is_active: bool = True
    rate_limit: int = 100  # requests per minute
    
    def is_valid(self) -> bool:
        """Check if key is valid"""
        if not self.is_active:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True


class AuthManager:
    """Manages API authentication"""
    
    def __init__(self):
        self._keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._key_hashes: Dict[str, str] = {}  # key_hash -> key_id
        self._enabled: bool = False  # Auth disabled by default
    
    def enable(self):
        """Enable authentication"""
        self._enabled = True
        print("[Auth] Authentication enabled")
    
    def disable(self):
        """Disable authentication"""
        self._enabled = False
        print("[Auth] Authentication disabled")
    
    @property
    def is_enabled(self) -> bool:
        """Check if auth is enabled"""
        return self._enabled
    
    def _hash_key(self, key: str) -> str:
        """Hash API key"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def generate_key(self, name: str, expires_in_days: Optional[int] = None) -> str:
        """Generate new API key"""
        # Generate random key
        raw_key = f"tun_{secrets.token_urlsafe(32)}"
        key_id = secrets.token_hex(8)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 86400)
        
        # Create API key record
        api_key = APIKey(
            key_id=key_id,
            key_hash=self._hash_key(raw_key),
            name=name,
            created_at=time.time(),
            expires_at=expires_at
        )
        
        self._keys[key_id] = api_key
        self._key_hashes[api_key.key_hash] = key_id
        
        print(f"[Auth] Generated key: {name} (ID: {key_id})")
        return raw_key
    
    def revoke_key(self, key_id: str) -> bool:
        """Revoke API key"""
        if key_id not in self._keys:
            return False
        
        api_key = self._keys[key_id]
        api_key.is_active = False
        
        # Remove from hash map
        if api_key.key_hash in self._key_hashes:
            del self._key_hashes[api_key.key_hash]
        
        print(f"[Auth] Revoked key: {key_id}")
        return True
    
    def validate_key(self, key: Optional[str]) -> bool:
        """Validate API key"""
        if not self._enabled:
            return True  # Auth disabled, allow all
        
        if not key:
            return False
        
        key_hash = self._hash_key(key)
        key_id = self._key_hashes.get(key_hash)
        
        if not key_id:
            return False
        
        api_key = self._keys.get(key_id)
        if not api_key:
            return False
        
        return api_key.is_valid()
    
    def get_key_info(self, key: str) -> Optional[APIKey]:
        """Get key info"""
        key_hash = self._hash_key(key)
        key_id = self._key_hashes.get(key_hash)
        
        if key_id:
            return self._keys.get(key_id)
        return None
    
    def list_keys(self) -> Dict[str, dict]:
        """List all keys"""
        return {
            key_id: {
                "name": key.name,
                "created_at": key.created_at,
                "expires_at": key.expires_at,
                "is_active": key.is_active,
                "rate_limit": key.rate_limit
            }
            for key_id, key in self._keys.items()
        }
    
    def load_keys_from_env(self, env_var: str = "TUNNEL_API_KEYS"):
        """Load keys from environment variable"""
        import os
        
        keys_str = os.getenv(env_var, "")
        if not keys_str:
            return
        
        for i, key in enumerate(keys_str.split(",")):
            key = key.strip()
            if key:
                key_id = f"env_{i}"
                api_key = APIKey(
                    key_id=key_id,
                    key_hash=self._hash_key(key),
                    name=f"Environment Key {i+1}",
                    created_at=time.time()
                )
                self._keys[key_id] = api_key
                self._key_hashes[api_key.key_hash] = key_id
        
        if self._keys:
            self.enable()
            print(f"[Auth] Loaded {len(self._keys)} keys from environment")


# Global auth manager instance
auth_manager = AuthManager()
