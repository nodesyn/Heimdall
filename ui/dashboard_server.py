"""
Standalone dashboard server
Serves the HTML/JS dashboard independently from the API
Injects API key and configuration from environment variables
"""

import os
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

class DashboardHandler(SimpleHTTPRequestHandler):
    """Serve dashboard with proper CORS headers and API key injection"""

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, api-key')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def do_GET(self):
        # Handle root path
        if self.path == '/':
            self.path = '/index.html'

        # Serve index.html with injected configuration
        if self.path == '/index.html':
            try:
                with open('index.html', 'r') as f:
                    content = f.read()

                # Get configuration from environment
                api_url = os.getenv('SIEM_API_URL', 'http://localhost:8010')
                api_key = os.getenv('SIEM_API_KEY', 'default-insecure-key-change-me')

                # Inject configuration before closing script tag
                config_script = f"""
        // Configuration injected by server
        window.API_CONFIG = {{
            api_url: '{api_url}',
            api_key: '{api_key}'
        }};
        """

                # Replace the API configuration in the script
                content = content.replace(
                    "// Auto-detect API URL - use same host as dashboard\n        const protocol = window.location.protocol;\n        const hostname = window.location.hostname;\n        const API_URL = localStorage.getItem('api_url') || `${protocol}//${hostname}:8010`;\n        const API_KEY = localStorage.getItem('api_key') || 'default-insecure-key-change-me';",
                    config_script + "\n        const API_URL = window.API_CONFIG.api_url || `${window.location.protocol}//${window.location.hostname}:8010`;\n        const API_KEY = window.API_CONFIG.api_key || 'default-insecure-key-change-me';"
                )

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Content-Length', len(content.encode()))
                self.end_headers()
                self.wfile.write(content.encode())
                return
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                return

        return super().do_GET()

    def log_message(self, format, *args):
        # Silent logging
        pass

if __name__ == '__main__':
    # Change to script directory
    os.chdir(os.path.dirname(__file__))

    port = int(os.getenv('DASHBOARD_PORT', 8501))
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)

    print(f"Dashboard server running on port {port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown requested")
        server.shutdown()
