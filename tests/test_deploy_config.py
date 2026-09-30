from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_deployment_has_health_and_tls_renewal_checks():
    compose = (ROOT / "docker-compose.yml").read_text()
    installer = (ROOT / "deploy/install.sh").read_text()
    nginx = (ROOT / "deploy/nginx.conf").read_text()
    assert "CMD-SHELL" in compose
    assert "certbot renew --dry-run" in installer
    assert "CUSTOM_DOMAINS" in nginx
