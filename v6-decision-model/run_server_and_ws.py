#!/usr/bin/env python3
"""Start and supervise the local model server and WebSocket proxy."""

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen
import venv


ROOT = Path(__file__).resolve().parent
PROXY = ROOT / "websocket-proxy"
ENV = ROOT / "env"
PYTHON = ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
LOCK_DIR = Path(tempfile.gettempdir()) / (
    "clam-servers-" + hashlib.sha256(
        str(ROOT).encode("utf-8")
    ).hexdigest()[:16]
)


class Lock:
    def __init__(self, name):
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        self.file = (LOCK_DIR / name).open("a+b")
        if self.file.tell() == 0:
            self.file.write(b"\0")
            self.file.flush()

    def acquire(self):
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        except OSError as exc:
            if os.name == "nt" and exc.errno in (13, 36):
                return False
            raise
        return True

    def close(self):
        self.file.close()


def local_host(host):
    if host in ("0.0.0.0", ""):
        return "127.0.0.1"
    if host == "::":
        return "::1"
    return host


def model_url():
    host = local_host(os.environ.get("D1_HOST", "0.0.0.0"))
    if ":" in host:
        host = f"[{host}]"
    return f"http://{host}:{int(os.environ.get('D1_PORT', '8430'))}"


def port_open(host, port):
    try:
        with socket.create_connection((local_host(host), port), timeout=1):
            return True
    except ConnectionRefusedError:
        return False
    except OSError as exc:
        raise RuntimeError(f"Cannot check {host}:{port}: {exc}") from exc


def model_running(url):
    try:
        with urlopen(url + "/health", timeout=2) as response:
            health = json.load(response)
    except (URLError, OSError, ValueError) as exc:
        raise RuntimeError(f"Port is occupied, but {url}/health failed: {exc}")
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise RuntimeError(f"Unexpected health response from {url}")
    if health.get("model_loaded") is not True:
        raise RuntimeError(f"Model server at {url} has no model loaded")
    return True


def websocket_running(host, port):
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    expected = base64.b64encode(hashlib.sha1(
        (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
    ).digest()).decode("ascii")
    request = (
        "GET / HTTP/1.1\r\n"
        f"Host: localhost:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    try:
        connection = socket.create_connection(
            (local_host(host), port), timeout=2
        )
    except ConnectionRefusedError:
        return False
    except OSError as exc:
        raise RuntimeError(f"WebSocket check failed on {host}:{port}: {exc}")
    try:
        with connection as s:
            s.sendall(request.encode("ascii"))
            response = b""
            while b"\r\n\r\n" not in response and len(response) < 16384:
                data = s.recv(4096)
                if not data:
                    break
                response += data
        lines = response.decode("iso-8859-1").split("\r\n")
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.lower()] = value.strip()
        if " 101 " in lines[0] and headers.get(
            "sec-websocket-accept"
        ) == expected:
            return True
    except OSError as exc:
        raise RuntimeError(f"WebSocket check failed on {host}:{port}: {exc}")
    raise RuntimeError(f"Port {host}:{port} is not a WebSocket server")


def ensure_environment(service):
    lock = Lock("environment")
    try:
        while not lock.acquire():
            time.sleep(0.2)
        if not PYTHON.is_file():
            if ENV.exists():
                raise RuntimeError(f"Missing environment Python: {PYTHON}")
            print(f"Creating virtual environment: {ENV}", flush=True)
            venv.create(ENV, with_pip=True)

        modules = (
            ["flask", "PIL", "yaml", "torch", "torchvision", "transformers"]
            if service == "model" else ["yaml", "websockets.asyncio.server"]
        )
        check = (
            "import importlib.util, sys\n"
            "if not (3, 10) <= sys.version_info[:2] <= (3, 14):\n"
            "    print('Environment requires Python 3.10 through 3.14', "
            "file=sys.stderr)\n"
            "    sys.exit(1)\n"
            "try:\n"
            "    missing = [m for m in sys.argv[1:] "
            "if importlib.util.find_spec(m) is None]\n"
            "except ModuleNotFoundError:\n"
            "    sys.exit(2)\n"
            "sys.exit(2 if missing else 0)\n"
        )
        result = subprocess.run([str(PYTHON), "-c", check, *modules])
        if result.returncode == 2:
            requirements = (
                ROOT / "requirements.txt" if service == "model"
                else PROXY / "requirements.txt"
            )
            print(f"Installing dependencies from {requirements}", flush=True)
            subprocess.run(
                [str(PYTHON), "-m", "pip", "install", "-r", str(requirements)],
                check=True,
            )
        elif result.returncode:
            raise RuntimeError(f"Could not check {service} dependencies")
    finally:
        lock.close()


def proxy_settings():
    spec = importlib.util.spec_from_file_location(
        "proxy_launcher_settings", PROXY / "settings.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load WebSocket settings")
    settings = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(settings)
    return settings.HOST, settings.PORT


def start_service(name, check_running, command):
    lock = Lock(name)
    keep_lock = False
    try:
        if not lock.acquire():
            print(f"{name} server is already running or starting.", flush=True)
            return None
        if check_running():
            print(f"{name} server is already running.", flush=True)
            return None
        ensure_environment(name)
        print(f"Starting {name} server...", flush=True)
        process = subprocess.Popen(command, cwd=ROOT)
        keep_lock = True
        return process, lock, name
    finally:
        if not keep_lock:
            lock.close()


def main():
    if not (3, 10) <= sys.version_info[:2] <= (3, 14):
        raise RuntimeError("Python 3.10 through 3.14 is required.")

    url = model_url()
    model_host = os.environ.get("D1_HOST", "0.0.0.0")
    model_port = int(os.environ.get("D1_PORT", "8430"))
    ws_host, ws_port = proxy_settings()
    services = (
        (
            "model",
            lambda: (
                port_open(model_host, model_port) and model_running(url)
            ),
            [str(PYTHON), str(ROOT / "server.py")],
        ),
        (
            "websocket", lambda: websocket_running(ws_host, ws_port),
            [str(PYTHON), str(PROXY / "server.py"), "--base-url", url],
        ),
    )
    children = []
    failed = False
    try:
        for service in services:
            try:
                child = start_service(*service)
                if child:
                    children.append(child)
            except (
                OSError, RuntimeError, subprocess.CalledProcessError
            ) as exc:
                print(f"Could not start {service[0]} server: {exc}",
                      file=sys.stderr, flush=True)
                failed = True
        if children:
            print(
                "Keep this window open; Ctrl+C stops its servers.", flush=True
            )
        while children:
            for child in children[:]:
                process, lock, name = child
                code = process.poll()
                if code is not None:
                    print(f"{name} server exited with code {code}.",
                          file=sys.stderr, flush=True)
                    failed = True
                    lock.close()
                    children.remove(child)
            time.sleep(0.5)
    finally:
        for process, lock, _ in children:
            if process.poll() is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
        for process, lock, _ in children:
            process.wait()
            lock.close()
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nServers stopped.")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Launcher failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
