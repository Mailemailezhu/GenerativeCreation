"""本地假接口：验证 API 方案的探活与 /images/edits 全链路，不发真请求。"""
import base64
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from PIL import Image, ImageDraw

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
IEND = b"IEND\xaeB`\x82"


def _pngs(body):
    """从 multipart 里按 PNG 头/尾硬切出两个文件：先 image 后 mask。"""
    out = []
    pos = 0
    while True:
        s = body.find(PNG_MAGIC, pos)
        if s < 0:
            break
        e = body.find(IEND, s)
        if e < 0:
            break
        out.append(body[s:e + len(IEND)])
        pos = e + len(IEND)
    return out


def fake_edit(img_bytes, mask_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    m = Image.open(io.BytesIO(mask_bytes)).convert("RGBA").getchannel("A")
    w, h = img.size
    if m.size != (w, h):
        m = m.resize((w, h))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 20, 20], fill=(255, 0, 255))  # 记号：证明确实是本服务画的
    px = m.load()
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if px[x, y] == 0:
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(120, 230, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.headers.get("Authorization") != "Bearer sk-mock":
            return self._json({"error": {"message": "invalid api key"}}, 401)
        if self.path.endswith("/models"):
            return self._json({"data": [{"id": "mock-edit-1"}, {"id": "mock-fast"}]})
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.headers.get("Authorization") != "Bearer sk-mock":
            return self._json({"error": {"message": "invalid api key"}}, 401)
        if not self.path.endswith("/images/edits"):
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n)
        files = _pngs(body)
        if len(files) < 2:
            return self._json({"error": {"message": "需要 image 和 mask 两个 PNG"}}, 400)
        out = fake_edit(files[0], files[1])
        return self._json({"data": [{"b64_json": base64.b64encode(out).decode()}]})


def serve(port=8931):
    srv = HTTPServer(("127.0.0.1", port), Handler)
    srv.serve_forever()


if __name__ == "__main__":
    serve()
