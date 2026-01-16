import http.server
import socketserver
import json
import re
import sys
from datetime import datetime

PORT = 4096

class MockHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/session":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"id": "mock_session_123"}).encode())
            return
        
        if "/message" in self.path:
            # Read request body to verify it's a prompt
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len).decode('utf-8')
            
            # Construct response
            # We want to match what's in docs/INDEX.md
            # Currently: "> **Last Updated:** 2026-01-06 00:00 UTC+11:00  " (or similar)
            # We will use a generic regex replacement or just a fixed string we saw earlier
            
            # Response structure
            response_content = {
                "status": "SUCCESS",
                "files_modified": [
                    {
                        "path": "docs/INDEX.md",
                        "change_type": "MODIFIED",
                        "hunks": [
                            {
                                "search": "# LifeOS Documentation Index — Last Updated: 2026-01-06",
                                "replace": "# LifeOS Documentation Index — Last Updated: 2026-01-07"
                            }
                        ]
                    }
                ],
                "summary": "Updated timestamp via Mock Server"
            }
            
            wrapped_response = {
                "parts": [
                    {
                        "type": "text",
                        "text": json.dumps(response_content)
                    }
                ]
            }
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(wrapped_response).encode())
            return

    def do_GET(self):
        if self.path == "/global/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

with socketserver.TCPServer(("", PORT), MockHandler) as httpd:
    print(f"Mock server serving on port {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
