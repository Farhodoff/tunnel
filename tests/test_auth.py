"""
Tests for authentication module
"""

import pytest
from tunnel.auth.manager import AuthManager, APIKey


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
