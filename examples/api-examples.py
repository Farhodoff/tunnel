"""
API Usage Examples
"""

import requests
import json

# Configuration
# Change this to your actual server URL
BASE_URL = "http://localhost:8080"  # or "https://localhost:8443" for HTTPS
API_KEY = "your_api_key"

# ============ AUTHENTICATION ============

# Connect with authentication (WebSocket)
# Client sends CONNECT message with auth_token
connect_message = {
    "msg_type": "connect",
    "payload": {
        "subdomain": "myapp",
        "local_port": 3000,
        "auth_token": API_KEY  # Authentication
    }
}

# ============ REST API EXAMPLES ============

# Health check
response = requests.get(f"{BASE_URL}/health")
print(f"Health: {response.json()}")

# List active tunnels
response = requests.get(f"{BASE_URL}/api/tunnels")
tunnels = response.json()
print(f"Active tunnels: {tunnels['active_tunnels']}")

# Get request logs
response = requests.get(f"{BASE_URL}/api/logs?limit=10")
logs = response.json()
print(f"Recent requests: {len(logs['logs'])}")

# Get metrics (Prometheus format)
response = requests.get(f"{BASE_URL}/metrics")
print(f"Metrics:\n{response.text[:500]}...")

# ============ WEBHOOK EXAMPLES ============

# Create webhook endpoint
response = requests.post(f"{BASE_URL}/webhooks/create")
webhook = response.json()
print(f"Webhook URL: {webhook['full_url']}")

# Send test webhook
requests.post(
    f"{BASE_URL}{webhook['url']}",
    json={"event": "test", "data": "hello"},
    headers={"Content-Type": "application/json"}
)

# Get captured webhooks
response = requests.get(f"{BASE_URL}/webhooks/requests/{webhook['endpoint_id']}")
captured = response.json()
print(f"Captured {captured['count']} requests")

# ============ ERROR HANDLING ============

def safe_request(method, url, **kwargs):
    """Make request with error handling"""
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except requests.exceptions.ConnectionError:
        print("Connection failed - server may be down")
    except requests.exceptions.Timeout:
        print("Request timeout")
    except Exception as e:
        print(f"Error: {e}")
    return None

# Example usage
result = safe_request("GET", f"{BASE_URL}/api/tunnels")
if result:
    print(f"Success: {result}")
