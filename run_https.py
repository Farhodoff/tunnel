#!/usr/bin/env python3
import uvicorn
from tunnel.server.app import app

print('='*50)
print('Tunnel Server (HTTPS)')
print('='*50)
print('Host: 0.0.0.0')
print('Port: 8443')
print('SSL: Enabled')
print('URL: https://localhost:8443')
print('='*50)

uvicorn.run(
    app,
    host='0.0.0.0',
    port=8443,
    ssl_certfile='certs/server.crt',
    ssl_keyfile='certs/server.key'
)
