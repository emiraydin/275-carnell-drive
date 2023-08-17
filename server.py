import requests
import json
from urllib.parse import urlparse
import os
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler


# Weird hack
SHOWCASE_INTERNAL_NAME = "showcase-internal.js"

class OurSimpleHTTPRequestHandler(SimpleHTTPRequestHandler):
    def send_error(self, code, message=None):
        if code == 404:
            logging.warning(
                f'404 error: {self.path} may not be downloading everything right')
        SimpleHTTPRequestHandler.send_error(self, code, message)


    def do_GET(self):
        global SHOWCASE_INTERNAL_NAME
        redirect_msg = None
        orig_request = self.path

        if self.path.startswith("/js/showcase.js") and os.path.exists(f"js/{SHOWCASE_INTERNAL_NAME}"):
            redirect_msg = "using our internal showcase.js file"
            self.path = f"/js/{SHOWCASE_INTERNAL_NAME}"

        if self.path.startswith("/locale/messages/strings_") and not os.path.exists(f".{self.path}"):
            redirect_msg = "original request was for a locale we do not have downloaded"
            self.path = "/locale/strings.json"
        raw_path, _, query = self.path.partition('?')
        if "crop=" in query and raw_path.endswith(".jpg"):
            query_args = urllib.parse.parse_qs(query)
            crop_addition = query_args.get("crop", None)
            if crop_addition is not None:
                crop_addition = f'crop={crop_addition[0]}'
            else:
                crop_addition = ''

            width_addition = query_args.get("width", None)
            if width_addition is not None:
                width_addition = f'width={width_addition[0]}_'
            else:
                width_addition = ''
            test_path = raw_path + width_addition + crop_addition + ".jpg"
            if os.path.exists(f".{test_path}"):
                self.path = test_path
                redirect_msg = "dollhouse/floorplan texture request that we have downloaded, better than generic texture file"
        if redirect_msg is not None or orig_request != self.path:
            logging.info(
                f'Redirecting {orig_request} => {self.path} as {redirect_msg}')


        SimpleHTTPRequestHandler.do_GET(self)
        return

    def do_POST(self):
        post_msg = None
        try:
            if self.path == "/api/mp/models/graph":
                self.send_response(200)
                self.end_headers()
                content_len = int(self.headers.get('content-length'))
                post_body = self.rfile.read(content_len).decode('utf-8')
                json_body = json.loads(post_body)
                option_name = json_body["operationName"]
                if option_name in GRAPH_DATA_REQ:
                    file_path = f"api/mp/models/graph_{option_name}.json"
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="UTF-8") as f:
                            self.wfile.write(f.read().encode('utf-8'))
                            post_msg = f"graph of operationName: {option_name} we are handling internally"
                            return
                    else:
                        post_msg = f"graph for operationName: {option_name} we don't know how to handle, but likely could add support, returning empty instead"

                self.wfile.write(bytes('{"data": "empty"}', "utf-8"))
                return
        except Exception as error:
            post_msg = f"Error trying to handle a post request of: {str(error)} this should not happen"
            pass
        finally:
            if post_msg is not None:
                logging.info(
                    f'Handling a post request on {self.path}: {post_msg}')

        self.do_GET()  # just treat the POST as a get otherwise:)

    def guess_type(self, path):
        res = SimpleHTTPRequestHandler.guess_type(self, path)
        if res == "text/html":
            return "text/html; charset=UTF-8"
        return res


GRAPH_DATA_REQ = {}

def openDirReadGraphReqs(path, pageId):
    for root, dirs, filenames in os.walk(path):
        for file in filenames:
            with open(os.path.join(root, file), "r", encoding="UTF-8") as f:
                GRAPH_DATA_REQ[file.replace(".json", "")] = f.read().replace("[MATTERPORT_MODEL_ID]",pageId)

os.chdir("vUb5e71k91Q")

try:
    logging.basicConfig(filename='server.log', encoding='utf-8', level=logging.DEBUG,  format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
except ValueError:
    logging.basicConfig(filename='server.log', level=logging.DEBUG,  format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logging.info("Server started up")


print("View in browser: http://127.0.0.1:8080")
httpd = HTTPServer(
    ('127.0.0.1', 8080), OurSimpleHTTPRequestHandler)
httpd.serve_forever()
