#!/usr/bin/env python3
"""KGPT Panel — 本地子 agent 管理面板。

派发 KGPT / Qwen 子 agent，在浏览器里实时查看它们的流式输出，
并支持对子 agent 的提问进行带记忆的回复（通过 codewhale --resume 续接会话）。

用法:
    python3 app.py
    然后浏览器打开 http://127.0.0.1:8787
"""

import json
import os
import re
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8787
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

tasks = {}
lock = threading.Lock()


def list_session_ids():
    """返回 codewhale 当前保存的所有 session id（8 位 hex 前缀）集合。"""
    try:
        out = subprocess.run(
            ["codewhale", "sessions"], capture_output=True, text=True, timeout=15
        ).stdout
        return set(re.findall(r"\b[0-9a-f]{8}\b", out))
    except Exception:
        return set()


def read_stream(task_id, proc):
    """把子进程的 stream-json 逐行解析成事件，追加到任务。"""
    for raw in proc.stdout:
        raw = raw.strip()
        if not raw:
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            ev = {"type": "raw", "content": raw}
        with lock:
            tasks[task_id]["events"].append(ev)
    proc.wait()


def run_task(task_id, provider, prompt):
    baseline = list_session_ids()
    cmd = [
        "codewhale", "--provider", provider,
        "exec", "--auto", "--output-format", "stream-json", prompt,
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.path.expanduser("~"),
        start_new_session=True,
    )
    with lock:
        tasks[task_id]["proc"] = proc
    read_stream(task_id, proc)
    time.sleep(1)  # 等 session 落盘
    new = list_session_ids() - baseline
    with lock:
        t = tasks[task_id]
        t["session_id"] = next(iter(new), None)
        t["status"] = "done" if proc.returncode == 0 else "failed"
        t["exit_code"] = proc.returncode
        t["proc"] = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif self.path == "/api/tasks":
            with lock:
                snap = [
                    {
                        "id": t["id"],
                        "provider": t["provider"],
                        "prompt": t["prompt"],
                        "status": t["status"],
                        "exit_code": t["exit_code"],
                        "created": t["created"],
                        "session_id": t.get("session_id"),
                        "events": list(t["events"]),
                    }
                    for t in tasks.values()
                ]
            self._send(200, json.dumps({"tasks": snap}, ensure_ascii=False),
                       "application/json; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        if self.path == "/api/run":
            provider = body.get("provider", "KGPT")
            prompt = (body.get("prompt") or "").strip()
            if not prompt:
                return self._send(400, json.dumps({"error": "prompt 不能为空"}),
                                  "application/json; charset=utf-8")
            task_id = uuid.uuid4().hex[:8]
            with lock:
                tasks[task_id] = {
                    "id": task_id,
                    "provider": provider,
                    "prompt": prompt,
                    "events": [],
                    "status": "running",
                    "exit_code": None,
                    "session_id": None,
                    "created": time.strftime("%H:%M:%S"),
                    "proc": None,
                }
            threading.Thread(target=run_task, args=(task_id, provider, prompt),
                             daemon=True).start()
            self._send(200, json.dumps({"task_id": task_id}),
                       "application/json; charset=utf-8")
        elif self.path.startswith("/api/stop/"):
            task_id = self.path.rsplit("/", 1)[-1]
            with lock:
                t = tasks.get(task_id)
            if t and t.get("proc"):
                try:
                    os.killpg(os.getpgid(t["proc"].pid), 15)  # SIGTERM
                except Exception:
                    t["proc"].terminate()
                with lock:
                    t["status"] = "stopped"
            self._send(200, json.dumps({"ok": True}), "application/json; charset=utf-8")
        elif self.path.startswith("/api/reply/"):
            task_id = self.path.rsplit("/", 1)[-1]
            message = (body.get("message") or "").strip()
            if not message:
                return self._send(400, json.dumps({"error": "回复内容不能为空"}),
                                  "application/json; charset=utf-8")
            with lock:
                t = tasks.get(task_id)
            if not t or not t.get("session_id"):
                return self._send(400, json.dumps(
                    {"error": "该任务没有可续接的会话（可能尚未完成，等任务结束后再回复）"}),
                    "application/json; charset=utf-8")
            cmd = [
                "codewhale", "--provider", t["provider"],
                "exec", "--resume", t["session_id"],
                "--auto", "--output-format", "stream-json", message,
            ]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=os.path.expanduser("~"),
                start_new_session=True,
            )
            with lock:
                t["status"] = "running"
                t["proc"] = proc
            threading.Thread(target=read_stream, args=(task_id, proc),
                             daemon=True).start()
            self._send(200, json.dumps({"ok": True}), "application/json; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"KGPT Panel 运行中: http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止", flush=True)


if __name__ == "__main__":
    main()
