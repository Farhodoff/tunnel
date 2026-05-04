"""
Tests for authentication module
"""

import pytest
from tunnel.auth.manager import AuthManager


class TestAuthManager:
    def setup_method(self):
        self.auth = AuthManager()
    
    def test_generate_key(self):
        key = self.auth.generate_key("Test Key")
        assert key.startswith("tun_")
        assert len(key) > 10
    
    def test_validate_key_disabled_auth(self):
        # When auth is disabled, all keys are valid
        assert self.auth.validate_key("any_key") == True
        assert self.auth.validate_key(None) == True
    
    def test_validate_key_enabled_auth(self):
        self.auth.enable()
        key = self.auth.generate_key("Test Key")
        
        assert self.auth.validate_key(key) == True
        assert self.auth.validate_key("invalid_key") == False
        assert self.auth.validate_key(None) == False
    
    def test_revoke_key(self):
        self.auth.enable()
        key = self.auth.generate_key("Test Key")
        
        # Get key info to find key_id
        info = self.auth.get_key_info(key)
        assert info is not None
        
        # Revoke
        result = self.auth.revoke_key(info.key_id)
        assert result == True
        
        # Should be invalid after revoke
        assert self.auth.validate_key(key) == False
    
    def test_list_keys(self):
        self.auth.generate_key("Key 1")
        self.auth.generate_key("Key 2")
        
        keys = self.auth.list_keys()
        assert len(keys) == 2

    def test_expired_key_is_invalid(self, monkeypatch):
        self.auth.enable()
        monkeypatch.setattr("tunnel.auth.manager.time.time", lambda: 1000.0)
        key = self.auth.generate_key("Expired Key", expires_in_days=1)

        monkeypatch.setattr("tunnel.auth.manager.time.time", lambda: 1000.0 + (2 * 86400))
        assert self.auth.validate_key(key) == False

    def test_load_keys_from_env_enables_auth(self, monkeypatch):
        monkeypatch.setenv("TUNNEL_API_KEYS", "key_one,key_two")
        self.auth.load_keys_from_env()

        assert self.auth.is_enabled == True
        assert self.auth.validate_key("key_one") == True
        assert self.auth.validate_key("key_two") == True
