import asyncio
import base64
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosedError

import chromites
import server
import settings
from server import MAX_MESSAGE_BYTES, handle_client


class SettingsTests(unittest.TestCase):
    def test_endpoint_override_precedence(self):
        cases = (
            ([], {}, "http://settings:8000"),
            (
                [],
                {"LM_STUDIO_BASE_URL": "http://env:1234"},
                "http://env:1234",
            ),
            (
                ["--base-url", "http://cli:9000/"],
                {"LM_STUDIO_BASE_URL": "http://env:1234"},
                "http://cli:9000",
            ),
        )
        for args, environ, expected in cases:
            with self.subTest(args=args, environ=environ):
                with (
                    patch.object(
                        settings, "DECISION_MODEL_ENDPOINT",
                        "http://settings:8000",
                    ),
                    patch.dict(os.environ, environ, clear=True),
                    patch.object(sys, "argv", ["server.py", *args]),
                    patch.object(
                        server, "run_server", new_callable=MagicMock
                    ) as run_server,
                    patch.object(server.asyncio, "run"),
                ):
                    server.main()
                run_server.assert_called_once_with(expected)


class RecordingChromite(chromites.Chromite):
    instances = []

    def __init__(self, client, path):
        super().__init__(client, path)
        self.events = []
        self.closed = asyncio.Event()
        self.instances.append(self)

    def on_create(self):
        self.events.append("create")

    def on_message(self, message):
        self.events.append(message)
        return super().on_message(message)

    def on_close(self):
        self.events.append("close")
        self.closed.set()


class ModelHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        if payload.get("fail"):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"model error")
            return
        response = json.dumps({
            "path": self.path,
            "received": payload,
            "answers": {"chill": {"type": "noul", "noul": 0.8}},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        pass


class ProxyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.prompts = tempfile.TemporaryDirectory()
        self.addCleanup(self.prompts.cleanup)
        prompt_dir = Path(self.prompts.name)
        for name in ("chromite", "chromite-3"):
            (prompt_dir / f"{name}.d.yaml").write_text(
                f"state: {name}\nquestions:\n  chill:\n    type: noul\n",
                encoding="utf-8",
            )
        (prompt_dir / "broken.d.yaml").write_text(
            "state: [invalid", encoding="utf-8"
        )
        self.enterContext(patch.object(chromites, "PROMPTS_DIR", prompt_dir))
        RecordingChromite.instances = []
        self.enterContext(patch("server.Chromite", RecordingChromite))
        self.model = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
        self.model_thread = threading.Thread(
            target=self.model.serve_forever, daemon=True
        )
        self.model_thread.start()
        base_url = f"http://127.0.0.1:{self.model.server_port}"
        self.proxy = await serve(
            partial(handle_client, base_url=base_url),
            "127.0.0.1",
            0,
            max_size=MAX_MESSAGE_BYTES,
        )
        port = self.proxy.sockets[0].getsockname()[1]
        self.url = f"ws://127.0.0.1:{port}"

    async def asyncTearDown(self):
        self.proxy.close()
        await self.proxy.wait_closed()
        await asyncio.to_thread(self.model.shutdown)
        self.model.server_close()
        self.model_thread.join()

    async def test_forwarding_and_errors_on_one_connection(self):
        payload = {
            "model": "chromite",
            "state": "hello",
            "questions": {"chill": {"type": "noul"}},
            "extra": ["unchanged"],
        }
        async with connect(f"{self.url}/chromite/") as socket:
            await socket.send(json.dumps(payload))
            result = json.loads(await socket.recv())
            self.assertEqual(result["path"], "/v1/systemone")
            self.assertEqual(result["received"], payload)
            self.assertEqual(result["answers"]["chill"]["noul"], 0.8)

            for message in ("not json", "[]", '{"fail": true}'):
                await socket.send(message)
                result = json.loads(await socket.recv())
                self.assertIn("error", result)

            await socket.send(json.dumps(payload))
            result = json.loads(await socket.recv())
            self.assertEqual(result["received"], payload)

    async def test_prompt_and_lifecycle_are_per_connection(self):
        async with connect(f"{self.url}/chromite") as first:
            async with connect(f"{self.url}/chromite-3/") as second:
                await first.send('{"model": "one"}')
                await second.send('{"model": "two"}')
                await first.recv()
                await second.recv()
                one, two = RecordingChromite.instances
                self.assertIsNot(one, two)
                self.assertEqual(one.prompt["state"], "chromite")
                self.assertEqual(two.prompt["state"], "chromite-3")
                self.assertEqual(one.events, ["create", {"model": "one"}])
                self.assertEqual(two.events, ["create", {"model": "two"}])
            await asyncio.wait_for(two.closed.wait(), timeout=2)
            self.assertEqual(two.events[-1], "close")
            self.assertNotIn("close", one.events)
        await asyncio.wait_for(one.closed.wait(), timeout=2)
        self.assertEqual(one.events[-1], "close")

    async def test_invalid_or_missing_prompts_are_rejected(self):
        for path in ("/wrong/", "/broken/", "/chromite/extra", "/../secret"):
            with self.subTest(path=path):
                async with connect(f"{self.url}{path}") as socket:
                    result = json.loads(await socket.recv())
                    self.assertIn("error", result)
                    with self.assertRaises(ConnectionClosedError) as error:
                        await socket.recv()
                    self.assertEqual(error.exception.rcvd.code, 1008)

    async def test_hooks_send_json_before_model_response(self):
        class SendingChromite(RecordingChromite):
            def on_create(self):
                self.to_client({"event": "ready"})

            def on_message(self, message):
                self.to_client({"event": "received", "payload": message})
                self.to_client({"event": "processing"})
                return message

        with patch("server.Chromite", SendingChromite):
            async with connect(f"{self.url}/chromite/") as socket:
                self.assertEqual(
                    json.loads(await socket.recv()), {"event": "ready"}
                )
                payload = {"model": "chromite"}
                await socket.send(json.dumps(payload))
                self.assertEqual(
                    json.loads(await socket.recv()),
                    {"event": "received", "payload": payload},
                )
                self.assertEqual(
                    json.loads(await socket.recv()), {"event": "processing"}
                )
                self.assertEqual(
                    json.loads(await socket.recv())["received"], payload
                )

    async def test_client_send_errors_are_visible(self):
        class FailingClient:
            async def send(self, data):
                raise RuntimeError("send failed")

        instance = chromites.Chromite(FailingClient(), "/chromite")
        with self.assertRaises(TypeError):
            instance.to_client({"bad": object()})
        with self.assertLogs("chromites", level="ERROR") as logs:
            task = instance.to_client({"event": "test"})
            with self.assertRaisesRegex(RuntimeError, "send failed"):
                await task
            await asyncio.sleep(0)
        self.assertIn("send failed", logs.output[0])

    async def test_example_builds_request_and_sends_one_response(self):
        class ExampleChromite(RecordingChromite):
            on_message = chromites.Chromite.example_on_message

        with patch("server.Chromite", ExampleChromite):
            async with connect(f"{self.url}/chromite/") as socket:
                await socket.send(json.dumps({"myfield": "Value"}))
                result = json.loads(await socket.recv())
                self.assertEqual(result["path"], "/v1/systemone")
                self.assertEqual(result["received"], {
                    "model": "YOUR_MODEL_ID",
                    "state": "chromite\n\nClient message: Value",
                    "questions": {"chill": {"type": "noul"}},
                    "images": [],
                })
                self.assertEqual(result["answers"]["chill"]["noul"], 0.8)
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(socket.recv(), timeout=0.1)

                await socket.send('{"myfield": 1}')
                result = json.loads(await socket.recv())
                self.assertIn("'myfield' must be a string", result["error"])

    async def test_async_hook_model_errors_reach_client(self):
        class ExampleChromite(RecordingChromite):
            async def on_message(self, message):
                await self.request_model({"fail": True})

        with patch("server.Chromite", ExampleChromite):
            async with connect(f"{self.url}/chromite/") as socket:
                await socket.send("{}")
                result = json.loads(await socket.recv())
                self.assertIn("HTTP 400", result["error"])

    async def test_browser_image_reaches_model_and_returns_one_response(self):
        image = "data:image/png;base64," + base64.b64encode(
            b"\x89PNG\r\n\x1a\nexample"
        ).decode("ascii")
        async with connect(f"{self.url}/chromite/") as socket:
            await socket.send(json.dumps({"image": image}))
            result = json.loads(await socket.recv())
            self.assertEqual(result["path"], "/v1/systemone")
            self.assertEqual(result["received"]["images"], [image])
            self.assertEqual(result["received"]["state"], "chromite")
            self.assertEqual(result["answers"]["chill"]["noul"], 0.8)
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(socket.recv(), timeout=0.1)

            await socket.send('{"image": null}')
            result = json.loads(await socket.recv())
            self.assertIn("'image' must be", result["error"])
            await socket.send(json.dumps({"image": image}))
            result = json.loads(await socket.recv())
            self.assertEqual(result["received"]["images"], [image])

    async def test_image_uses_configured_model_and_live_prompt_setting(self):
        prompt = Path(self.prompts.name) / "chromite.d.yaml"
        image = "data:image/png;base64,example"
        with patch.object(settings, "MODEL", "configured-model"):
            async with connect(f"{self.url}/chromite/") as socket:
                prompt.write_text(
                    "state: updated\nquestions:\n  chill:\n    type: noul\n",
                    encoding="utf-8",
                )
                await socket.send(json.dumps({"image": image}))
                result = json.loads(await socket.recv())
                self.assertEqual(
                    result["received"]["model"], "configured-model"
                )
                self.assertEqual(result["received"]["state"], "updated")

            with patch.object(chromites.Chromite, "live_prompt", False):
                async with connect(f"{self.url}/chromite/") as socket:
                    prompt.write_text(
                        "state: changed\nquestions:\n  chill:\n"
                        "    type: noul\n",
                        encoding="utf-8",
                    )
                    await socket.send(json.dumps({"image": image}))
                    result = json.loads(await socket.recv())
                    self.assertEqual(result["received"]["state"], "updated")

    async def test_listener_uses_configured_host_port_and_message_limit(self):
        with (
            patch.object(settings, "HOST", "127.0.0.1"),
            patch.object(settings, "PORT", 4321),
            patch.object(server, "MAX_MESSAGE_BYTES", 1234),
            patch.object(server, "serve", side_effect=RuntimeError("stop"))
            as serve_mock,
        ):
            with self.assertRaisesRegex(RuntimeError, "stop"):
                await server.run_server("http://model")
        args, kwargs = serve_mock.call_args
        self.assertEqual(args[1:], ("127.0.0.1", 4321))
        self.assertEqual(kwargs["max_size"], 1234)
        self.assertEqual(args[0].keywords["base_url"], "http://model")

    async def test_local_image_is_loaded_relative_to_chromites(self):
        instance = chromites.Chromite(None, "/chromite")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "images").mkdir()
            content = b"\xff\xd8\xffexample"
            (base / "images" / "my-image.jpg").write_bytes(content)
            with patch.object(chromites, "__file__", str(base / "chromites.py")):
                self.assertEqual(
                    instance.example_load_local_image(),
                    "data:image/jpeg;base64,"
                    + base64.b64encode(content).decode("ascii"),
                )
                (base / "images" / "my-image.jpg").unlink()
                with self.assertRaisesRegex(RuntimeError, "Could not load"):
                    instance.example_load_local_image()

    async def test_image_message_can_exceed_default_websocket_limit(self):
        image = "data:image/png;base64," + base64.b64encode(
            b"\x89PNG\r\n\x1a\n" + b"x" * (1024 * 1024)
        ).decode("ascii")
        async with connect(
            f"{self.url}/chromite/", max_size=MAX_MESSAGE_BYTES
        ) as socket:
            await socket.send(json.dumps({"image": image}))
            result = json.loads(await socket.recv())
            self.assertEqual(result["received"]["images"], [image])


if __name__ == "__main__":
    unittest.main()
