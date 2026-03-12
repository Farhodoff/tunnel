"""
Custom domain support for tunnels
Allow users to use their own domains instead of subdomains
"""

import json
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class CustomDomain:
    """Represents a custom domain configuration"""
    id: str
    domain: str
    subdomain: str  # Internal subdomain mapping
    user_id: Optional[str]
    api_key: str
    created_at: str
    verified: bool = False
    verification_token: str = ""
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'domain': self.domain,
            'subdomain': self.subdomain,
            'user_id': self.user_id,
            'api_key': self.api_key[:8] + '...' if self.api_key else None,  # Mask API key
            'created_at': self.created_at,
            'verified': self.verified,
            'ssl_enabled': self.ssl_enabled,
            'active': self.active
        }


class CustomDomainManager:
    """Manages custom domains for tunnels"""
    
    def __init__(self):
        self.domains: Dict[str, CustomDomain] = {}  # domain -> CustomDomain
        self.subdomain_map: Dict[str, str] = {}  # subdomain -> domain
        self.verification_tokens: Dict[str, str] = {}  # token -> domain
    
    def register_domain(self, domain: str, api_key: str, 
                       user_id: Optional[str] = None) -> CustomDomain:
        """Register a new custom domain"""
        if domain in self.domains:
            raise ValueError(f"Domain {domain} is already registered")
        
        # Generate internal subdomain
        subdomain = f"custom_{str(uuid.uuid4())[:8]}"
        
        # Generate verification token
        verification_token = str(uuid.uuid4())
        
        custom_domain = CustomDomain(
            id=str(uuid.uuid4())[:8],
            domain=domain,
            subdomain=subdomain,
            user_id=user_id,
            api_key=api_key,
            created_at=datetime.utcnow().isoformat(),
            verified=False,
            verification_token=verification_token
        )
        
        self.domains[domain] = custom_domain
        self.subdomain_map[subdomain] = domain
        self.verification_tokens[verification_token] = domain
        
        return custom_domain
    
    def verify_domain(self, domain: str, token: str) -> bool:
        """Verify domain ownership using token"""
        if domain not in self.domains:
            return False
        
        custom_domain = self.domains[domain]
        
        if custom_domain.verification_token == token:
            custom_domain.verified = True
            return True
        
        return False
    
    def get_verification_instructions(self, domain: str) -> Dict[str, Any]:
        """Get DNS verification instructions"""
        if domain not in self.domains:
            return {'error': 'Domain not found'}
        
        custom_domain = self.domains[domain]
        
        return {
            'domain': domain,
            'verification_token': custom_domain.verification_token,
            'instructions': [
                {
                    'type': 'DNS_TXT',
                    'name': f'_tunnel-verify.{domain}',
                    'value': custom_domain.verification_token,
                    'description': 'Add a TXT record with this value'
                },
                {
                    'type': 'DNS_CNAME',
                    'name': domain,
                    'value': f'{custom_domain.subdomain}.tunnel.example.com',
                    'description': 'Point your domain to this CNAME'
                }
            ],
            'verification_url': f'/api/domains/{domain}/verify'
        }
    
    def get_domain(self, domain: str) -> Optional[CustomDomain]:
        """Get custom domain by domain name"""
        return self.domains.get(domain)
    
    def get_domain_by_subdomain(self, subdomain: str) -> Optional[CustomDomain]:
        """Get custom domain by internal subdomain"""
        if subdomain in self.subdomain_map:
            domain = self.subdomain_map[subdomain]
            return self.domains.get(domain)
        return None
    
    def list_domains(self, user_id: Optional[str] = None, 
                    api_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """List custom domains with optional filtering"""
        domains = list(self.domains.values())
        
        if user_id:
            domains = [d for d in domains if d.user_id == user_id]
        
        if api_key:
            domains = [d for d in domains if d.api_key == api_key]
        
        return [d.to_dict() for d in domains]
    
    def update_domain(self, domain: str, **kwargs) -> Optional[CustomDomain]:
        """Update custom domain settings"""
        if domain not in self.domains:
            return None
        
        custom_domain = self.domains[domain]
        
        # Update allowed fields
        if 'ssl_enabled' in kwargs:
            custom_domain.ssl_enabled = kwargs['ssl_enabled']
        if 'ssl_cert_path' in kwargs:
            custom_domain.ssl_cert_path = kwargs['ssl_cert_path']
        if 'ssl_key_path' in kwargs:
            custom_domain.ssl_key_path = kwargs['ssl_key_path']
        if 'active' in kwargs:
            custom_domain.active = kwargs['active']
        
        return custom_domain
    
    def delete_domain(self, domain: str) -> bool:
        """Delete a custom domain"""
        if domain not in self.domains:
            return False
        
        custom_domain = self.domains[domain]
        
        # Clean up mappings
        del self.domains[domain]
        del self.subdomain_map[custom_domain.subdomain]
        del self.verification_tokens[custom_domain.verification_token]
        
        return True
    
    def is_custom_domain(self, host: str) -> bool:
        """Check if host is a registered custom domain"""
        return host in self.domains
    
    def get_subdomain_for_domain(self, host: str) -> Optional[str]:
        """Get internal subdomain for a custom domain"""
        if host in self.domains:
            return self.domains[host].subdomain
        return None
    
    def validate_domain_config(self, domain: str) -> Dict[str, Any]:
        """Validate domain configuration"""
        if domain not in self.domains:
            return {'valid': False, 'error': 'Domain not registered'}
        
        custom_domain = self.domains[domain]
        
        issues = []
        
        if not custom_domain.verified:
            issues.append('Domain not verified')
        
        if not custom_domain.active:
            issues.append('Domain is inactive')
        
        if custom_domain.ssl_enabled:
            if not custom_domain.ssl_cert_path or not custom_domain.ssl_key_path:
                issues.append('SSL enabled but certificates not configured')
        
        return {
            'valid': len(issues) == 0,
            'domain': domain,
            'verified': custom_domain.verified,
            'active': custom_domain.active,
            'ssl_enabled': custom_domain.ssl_enabled,
            'issues': issues
        }


# Global instance
custom_domain_manager = CustomDomainManager()
