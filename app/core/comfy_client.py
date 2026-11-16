"""ComfyUI 引擎 HTTP 客户端（零依赖，仅标准库）。"""

import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request

# ComfyUI 只把执行/采样事件推给提交任务的 client_id，界面订阅 websocket 时必须用同一个值
CLIENT_ID = "gc-ui"


class ComfyError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, host="127.0.0.1", port=8188, timeout=15.0):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def _open(self, req, timeout=None):
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            raise ComfyError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}") from e
        except urllib.error.URLError as e:
            raise ComfyError(f"无法连接引擎 {self.base}: {e.reason}") from e

    def _get(self, path, timeout=None):
        return self._open(urllib.request.Request(self.base + path), timeout)

    def _post_json(self, path, payload, timeout=None):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base + path, data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        return self._open(req, timeout)

    def is_up(self):
        try:
            self._get("/system_stats", timeout=3)
            return True
        except ComfyError:
            return False

    def stats(self):
        return json.loads(self._get("/system_stats"))

    def upload_image(self, path):
        """上传本地图片到引擎 input 目录，返回引擎内文件名。"""
        name = os.path.basename(path)
        with open(path, "rb") as f:
            raw = f.read()
        boundary = "----GCBoundary7MA4YWxkTrZu0gW"
        ctype = mimetypes.guess_type(name)[0] or "image/png"
        body = b"\r\n".join([
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{name}"'.encode(),
            f"Content-Type: {ctype}".encode(),
            b"",
            raw,
            f"--{boundary}".encode(),
            b'Content-Disposition: form-data; name="overwrite"',
            b"",
            b"true",
            f"--{boundary}--".encode(),
            b"",
        ])
        req = urllib.request.Request(
            self.base + "/upload/image", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST")
        return json.loads(self._open(req, timeout=60))["name"]

    def queue_prompt(self, workflow, client_id=CLIENT_ID):
        resp = json.loads(self._post_json("/prompt", {"prompt": workflow, "client_id": client_id}))
        if "prompt_id" not in resp:
            raise ComfyError(f"提交失败: {resp}")
        return resp["prompt_id"]

    def wait_for(self, prompt_id, timeout=300.0, poll=1.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            entry = json.loads(self._get(f"/history/{prompt_id}")).get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    raise ComfyError(f"引擎执行出错: {status}")
                if entry.get("outputs"):
                    return entry
            time.sleep(poll)
        raise ComfyError(f"等待结果超时 {timeout}s")

    def fetch_image(self, filename, subfolder="", folder_type="output"):
        q = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
        return self._get(f"/view?{q}", timeout=60)

    def save_image(self, filename, out_path, subfolder="", folder_type="output"):
        data = self.fetch_image(filename, subfolder, folder_type)
        with open(out_path, "wb") as f:
            f.write(data)
        return out_path


def first_image(entry):
    """从 history 条目里取第一张输出图片的 (filename, subfolder, type)。"""
    for node in (entry.get("outputs") or {}).values():
        for img in (node.get("images") or []):
            return img.get("filename"), img.get("subfolder", ""), img.get("type", "output")
    raise ComfyError("输出里没有图片")
