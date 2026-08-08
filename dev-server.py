import http.server
import urllib.parse
import json
import os

class DevHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def translate_path(self, path):
        # Remove query parameters and leading slash
        clean = path.split("?", 1)[0].lstrip("/")
        
        if clean == "" or clean == "index.html":
            return os.path.abspath("assets/index.html")

        # Check exact path in assets/
        full = os.path.abspath(os.path.join("assets", clean))
        if os.path.exists(full):
            return full

        # Try tile folder hyphen stripping
        if "/tiles/" in clean or "tiles/" in clean:
            parts = clean.split("/")
            modified = False
            for i, p in enumerate(parts):
                if len(p) == 36 and p.count("-") == 4:
                    parts[i] = p.replace("-", "")
                    modified = True
            if modified:
                alt = "/".join(parts)
                alt_full = os.path.abspath(os.path.join("assets", alt))
                if os.path.exists(alt_full):
                    return alt_full
                # Also try swapping mesh_tiles/~/ or ~/tiles
                if "/~/tiles/" in alt:
                    alt2 = alt.replace("/~/tiles/", "/tiles/~/")
                    alt2_full = os.path.abspath(os.path.join("assets", alt2))
                    if os.path.exists(alt2_full):
                        return alt2_full

        # Try key rewrites for mesh_tiles / tilde paths
        if "/~/mesh_tiles/" in clean:
            alt = clean.replace("/~/mesh_tiles/", "/mesh_tiles/~/")
            alt_full = os.path.abspath(os.path.join("assets", alt))
            if os.path.exists(alt_full):
                return alt_full

        if "/mesh_tiles/~/" in clean:
            alt = clean.replace("/mesh_tiles/~/", "/~/mesh_tiles/")
            alt_full = os.path.abspath(os.path.join("assets", alt))
            if os.path.exists(alt_full):
                return alt_full

        if "/~/" in clean:
            alt = clean.replace("/~/", "/")
            alt_full = os.path.abspath(os.path.join("assets", alt))
            if os.path.exists(alt_full):
                return alt_full

        return super().translate_path(path)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)

        if url.path == "/js/showcase.js":
            self.path = "/js/showcase-internal.js"
            url = urllib.parse.urlparse(self.path)

        # Handle /public-access
        if "/public-access" in url.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"token":"dummy_token_12345"}')
            return

        # Handle /api/player/models/.../files?type=N
        if url.path.endswith("/files"):
            query = urllib.parse.parse_qs(url.query)
            if "type" in query:
                type_val = query["type"][0]
                target = f"{url.path}_type{type_val}"
                if os.path.exists(os.path.join("assets", target.lstrip("/"))):
                    self.path = target
                    url = urllib.parse.urlparse(self.path)

        # Handle crop query params for jpg
        if "crop=" in url.query and url.path.endswith(".jpg"):
            query = urllib.parse.parse_qs(url.query)
            crop = query.get("crop", [""])[0]
            width = query.get("width", [""])[0]
            w_part = f"width={width}_" if width else ""
            c_part = f"crop={crop}"
            test_path = f"{url.path}{w_part}{c_part}.jpg"
            if os.path.exists(os.path.join("assets", test_path.lstrip("/"))):
                self.path = test_path
                url = urllib.parse.urlparse(self.path)

        # Handle locale fallback
        if url.path.startswith("/locale/messages/strings_") and not os.path.exists(os.path.join("assets", url.path.lstrip("/"))):
            self.path = "/locale/strings.json"
            url = urllib.parse.urlparse(self.path)

        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/mp/models/graph"):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                op_name = data.get("operationName")
                if op_name:
                    file_path = f"assets/api/mp/models/graph_{op_name}.json"
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            resp = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.end_headers()
                        self.wfile.write(resp)
                        return
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"data":"empty"}')
            return

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-matterport-application-name")
        self.end_headers()

if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", 8080), DevHandler)
    print("Dev server running on http://127.0.0.1:8080")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
