"""验证实时通道：登录 -> WebSocket 握手 -> 统计推送速率与通知。

不依赖第三方库，用于 CI 或本机快速验收。
用法：
    python deploy/scripts/check_ws.py               # 5 秒采样
    python deploy/scripts/check_ws.py 127.0.0.1 18080 8
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import sys
import time
import urllib.request

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 18080
SECONDS = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0


def login() -> str:
    request = urllib.request.Request(
        f"http://{HOST}:{PORT}/api/v1/auth/login",
        data=json.dumps({"username": "manager", "password": "demo1234"}).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["data"]["token"]


def read_frame(sock: socket.socket) -> tuple[int, bytes]:
    header = sock.recv(2)
    if len(header) < 2:
        raise RuntimeError("连接被关闭")
    opcode = header[0] & 0x0F
    length = header[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", sock.recv(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", sock.recv(8))[0]
    payload = b""
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        if not chunk:
            break
        payload += chunk
    return opcode, payload


def main() -> int:
    token = login()
    print(f"[1] login      -> token 长度 {len(token)}")

    key = base64.b64encode(os.urandom(16)).decode()
    sock = socket.create_connection((HOST, PORT), timeout=10)
    sock.sendall((
        f"GET /ws/live?token={token} HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Origin: http://127.0.0.1\r\n\r\n"
    ).encode())

    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
    status_line = response.split(b"\r\n", 1)[0].decode(errors="replace")
    print(f"[2] handshake  -> {status_line}")
    if "101" not in status_line:
        print("结果：未通过（WebSocket 未升级成功）")
        return 1

    sock.settimeout(SECONDS + 5)
    started = time.time()
    counts: dict[str, int] = {}
    notices: list[dict] = []
    last_seq = 0
    while time.time() - started < SECONDS:
        opcode, payload = read_frame(sock)
        if opcode != 0x1:
            continue
        message = json.loads(payload.decode("utf-8"))
        message_type = message.get("type", "?")
        counts[message_type] = counts.get(message_type, 0) + 1
        if message_type == "frames":
            last_seq = (message.get("payload") or {}).get("seq", last_seq)
        elif message_type == "system.notice":
            notices.append(message.get("payload") or {})

    elapsed = time.time() - started
    sock.close()

    frames = counts.get("frames", 0)
    rate = frames / elapsed if elapsed else 0
    print(f"[3] frames     -> {frames} 帧 / {elapsed:.1f}s = {rate:.1f} Hz，最后 seq={last_seq}")
    for notice in notices:
        print(f"[4] notice     -> level={notice.get('level')} message={notice.get('message')}")

    if frames == 0:
        print("结果：未通过（没有收到 frames）")
        return 1
    if rate < 5:
        print(f"结果：未通过（推送速率 {rate:.1f} Hz 低于 5 Hz）")
        return 1

    print(f"结果：通过（推送 {rate:.1f} Hz，通知 {len(notices)} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
