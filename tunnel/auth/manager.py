"""
Authentication Manager - API key management
"""

import secrets
import hashlib
import time
from typing import Dict, Optional, Set
from dataclasses import dataclass, field

from tunnel.utils.logging import setup_logger

logger = setup_logger("tunnel.auth")


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
    """Manages API authentication (env + JSON file persistence)"""
    
    def __init__(self, file_path: Optional[str] = None):
        self._keys: Dict[str, APIKey] = {}  # key_id -> APIKey
        self._key_hashes: Dict[str, str] = {}  # key_hash -> key_id
        self._enabled: bool = False  # Auth disabled by default
        self._file: Optional[str] = file_path
    
    def enable(self):
        """Enable authentication"""
        self._enabled = True
        logger.info("Authentication enabled")
    
    def disable(self):
        """Disable authentication"""
        self._enabled = False
        logger.info("Authentication disabled")
    
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
        
        # Creating a key turns auth on (fail-closed from then on)
        if not self._enabled:
            self.enable()
        logger.info(f"Generated key: {name} (ID: {key_id})")
        self._persist()
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
        
        logger.info(f"Revoked key: {key_id}")
        self._persist()
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
            logger.info(f"Loaded {len(self._keys)} keys from environment")
    
    def configure_file(self, path: Optional[str]):
        """Set JSON persistence file (None = disable)"""
        self._file = path or None
    
    def configure_from_env(self, keys_var: str = "TUNNEL_API_KEYS",
                           file_var: str = "TUNNEL_API_KEYS_FILE"):
        """Load file first, then env (env keys win, are not persisted)"""
        import os
        self.configure_file(os.getenv(file_var, self._file or ""))
        if self._file:
            try:
                self.load_from_file(self._file)
            except FileNotFoundError:
                pass  # first run, file created on first generate
            except Exception as e:
                logger.warning(f"Failed to load keys file ({e})")
        self.load_keys_from_env(keys_var)
        return self
    
    def save_to_file(self, path: Optional[str] = None) -> int:
        """Persist hashed key records to JSON. Returns count saved."""
        import json
        target = path or self._file
        if not target:
            return 0
        data = [
            {
                "key_id": k.key_id,
                "key_hash": k.key_hash,
                "name": k.name,
                "created_at": k.created_at,
                "expires_at": k.expires_at,
                "is_active": k.is_active,
                "rate_limit": k.rate_limit,
            }
            for k in self._keys.values()
            if not k.key_id.startswith("env_")  # env keys are config, not state
        ]
        with open(target, "w") as f:
            json.dump(data, f, indent=2)
        return len(data)
    
    def load_from_file(self, path: Optional[str] = None) -> int:
        """Load hashed key records from JSON. Returns count loaded."""
        import json
        import os
        target = path or self._file
        if not target:
            return 0
        if not os.path.exists(target):
            raise FileNotFoundError(target)
        with open(target) as f:
            data = json.load(f)
        loaded = 0
        for item in data:
            key_id = item.get("key_id", "")
            if not key_id or key_id in self._keys:
                continue
            api_key = APIKey(
                key_id=key_id,
                key_hash=item.get("key_hash", ""),
                name=item.get("name", key_id),
                created_at=item.get("created_at", time.time()),
                expires_at=item.get("expires_at"),
                is_active=item.get("is_active", True),
                rate_limit=item.get("rate_limit", 100),
            )
            if not api_key.key_hash:
                continue
            self._keys[key_id] = api_key
            if api_key.is_valid():
                self._key_hashes[api_key.key_hash] = key_id
            loaded += 1
        if loaded:
            self.enable()
            logger.info(f"Loaded {loaded} keys from file")
        return loaded
    
    def _persist(self):
        """Best-effort auto-save after mutations"""
        if not self._file:
            return
        try:
            self.save_to_file()
        except Exception as e:
            logger.warning(f"Failed to save keys file ({e})")


# Global auth manager instance
auth_manager = AuthManager()
