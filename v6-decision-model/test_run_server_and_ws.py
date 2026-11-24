import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "launcher", ROOT / "run_server_and_ws.py"
)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok","model_loaded":true}')

    def log_message(self, format, *args):
        pass


class LauncherTests(unittest.TestCase):
    def test_model_health_and_occupied_wrong_port(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_port
        self.assertTrue(launcher.port_open("127.0.0.1", port))
        self.assertTrue(launcher.model_running(f"http://127.0.0.1:{port}"))
        with self.assertRaises(RuntimeError):
            launcher.websocket_running("127.0.0.1", port)

    def test_websocket_handshake(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        def respond():
            with listener:
                conn, _ = listener.accept()
                with conn:
                    request = conn.recv(4096).decode("ascii")
                    key = next(
                        line.split(": ", 1)[1]
                        for line in request.split("\r\n")
                        if line.startswith("Sec-WebSocket-Key:")
                    )
                    digest = hashlib.sha1(
                        (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
                        .encode("ascii")
                    ).digest()
                    accept = base64.b64encode(digest).decode("ascii")
                    conn.sendall((
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
                    ).encode("ascii"))

        thread = threading.Thread(target=respond)
        thread.start()
        self.addCleanup(thread.join)
        self.assertTrue(launcher.websocket_running("127.0.0.1", port))

    def test_startup_lock_prevents_duplicates_and_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(launcher, "LOCK_DIR", Path(directory)),
                patch.object(launcher, "ensure_environment") as setup,
                patch.object(launcher.subprocess, "Popen") as popen,
            ):
                args = ("model", lambda: False, ["server"])
                first = launcher.start_service(*args)
                self.assertIsNotNone(first)
                self.assertIsNone(launcher.start_service(*args))
                self.assertEqual(popen.call_count, 1)
                self.assertEqual(setup.call_count, 1)
                first[1].close()
                replacement = launcher.start_service(*args)
                self.assertIsNotNone(replacement)
                self.assertEqual(popen.call_count, 2)
                replacement[1].close()

    def test_lock_is_shared_between_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(launcher, "LOCK_DIR", Path(directory)):
                lock = launcher.Lock("model")
                self.assertTrue(lock.acquire())
                self.addCleanup(lock.close)
                probe = (
                    "import importlib.util, pathlib, sys; "
                    "spec = importlib.util.spec_from_file_location("
                    "'launcher', sys.argv[1]); "
                    "module = importlib.util.module_from_spec(spec); "
                    "spec.loader.exec_module(module); "
                    "module.LOCK_DIR = pathlib.Path(sys.argv[2]); "
                    "lock = module.Lock('model'); "
                    "print(lock.acquire()); lock.close()"
                )
                command = [
                    sys.executable, "-c", probe,
                    str(ROOT / "run_server_and_ws.py"), directory,
                ]
                result = subprocess.run(
                    command, check=True, capture_output=True, text=True
                )
                self.assertEqual(result.stdout.strip(), "False")
                lock.close()
                result = subprocess.run(
                    command, check=True, capture_output=True, text=True
                )
                self.assertEqual(result.stdout.strip(), "True")

    def test_existing_service_skips_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(launcher, "LOCK_DIR", Path(directory)),
                patch.object(launcher, "ensure_environment") as setup,
                patch.object(launcher.subprocess, "Popen") as popen,
            ):
                result = launcher.start_service(
                    "websocket", lambda: True, ["server"]
                )
                self.assertIsNone(result)
                setup.assert_not_called()
                popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
