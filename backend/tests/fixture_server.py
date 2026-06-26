import http.server
import os
import socketserver

PORT = 8081
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "images")

class FixtureHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ASSETS_DIR, **kwargs)

class ThreadingSimpleServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def start_server():
    Handler = FixtureHandler
    with ThreadingSimpleServer(("", PORT), Handler) as httpd:
        print(f"Fixture Server serving {ASSETS_DIR} at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    start_server()
