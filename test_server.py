#!/usr/bin/env python3
"""Simple test HTTP server"""

import http.server
import socketserver
import json

PORT = 3333

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {
            "message": "Hello from local server!",
            "path": self.path,
            "status": "ok"
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""
        
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {
            "message": "POST received",
            "path": self.path,
            "body": body
        }
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        print(f"[LocalServer] {args[0]}")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"[LocalServer] Serving on port {PORT}")
    httpd.serve_forever()
