"""
SSL/TLS utilities for HTTPS support
"""

import os
import ssl
from pathlib import Path
from typing import Tuple, Optional


def get_ssl_context(cert_path: Optional[str] = None, 
                    key_path: Optional[str] = None) -> Optional[ssl.SSLContext]:
    """Create SSL context for HTTPS"""
    
    # If paths provided, use them
    if cert_path and key_path:
        if os.path.exists(cert_path) and os.path.exists(key_path):
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(cert_path, key_path)
            return context
        else:
            print(f"[SSL] Certificate files not found: {cert_path}, {key_path}")
            return None
    
    # Check for environment variables
    cert_path = os.getenv("TUNNEL_SSL_CERT")
    key_path = os.getenv("TUNNEL_SSL_KEY")
    
    if cert_path and key_path:
        if os.path.exists(cert_path) and os.path.exists(key_path):
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(cert_path, key_path)
            print(f"[SSL] Loaded certificates from environment")
            return context
    
    return None


def generate_self_signed_cert(hostname: str = "localhost") -> Tuple[str, str]:
    """Generate self-signed certificate for development"""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime
    
    # Generate key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Generate certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Tunnel"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(hostname),
            x509.DNSName(f"*.{hostname}"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())
    
    # Save to files
    cert_dir = Path("certs")
    cert_dir.mkdir(exist_ok=True)
    
    cert_path = cert_dir / "server.crt"
    key_path = cert_dir / "server.key"
    
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    return str(cert_path), str(key_path)


# Import ipaddress for generate_self_signed_cert
import ipaddress
