# Decision-model WebSocket proxy

On Windows, double-click [run.bat](./run.bat). It uses the parent `env/`,
creating it and installing the proxy dependencies if needed.

Alternatively, install the proxy dependencies and start it manually:

```bash
python3 -m pip install -r v6-decision-model/websocket-proxy/requirements.txt
python3 v6-decision-model/websocket-proxy/server.py \
  --base-url http://127.0.0.1:8000
```

Edit [settings.py](./settings.py) to configure:

- `MODEL`: model ID included in requests built by the example hooks.
- `DECISION_MODEL_ENDPOINT`: HTTP server base URL, without `/v1/systemone`.
- `HOST` and `PORT`: WebSocket listening address and port.
- `MAX_MESSAGE_BYTES`: maximum incoming WebSocket message size, including
  JSON and base64. The image example page also has a 64 MiB limit.
- `PROMPTS_DIR`: directory containing the `*.d.yaml` prompt files.
- `LIVE_PROMPT`: reload the selected prompt before each example request.

Restart the proxy after editing settings. `--base-url` overrides
`LM_STUDIO_BASE_URL`, which overrides `DECISION_MODEL_ENDPOINT`. If the
endpoint requires authentication, set `LM_STUDIO_API_TOKEN` on the proxy
host; do not put tokens in settings.

Open [index.html](./index.html) in a browser on the same machine and connect to
`ws://localhost:9999/chromite/`. The page supports light and dark modes.

The connection path selects a prompt in `../prompts/`: for example,
`/chromite-3` or `/chromite-3/` loads `chromite-3.d.yaml`. The file must
already exist. Each connection creates a separate `Chromite` instance in
[chromites.py](./chromites.py), with `client`, `path`, `prompt_path`, and
the loaded `prompt` available to its `on_create`, `on_message`, and `on_close`
hooks. `on_message` receives a JSON object and may return an object to forward.
The hooks can be extended for per-connection state. `on_create` and `on_close`
are synchronous; `on_message` may also be asynchronous.
Call `self.to_client({"event": "ready"})` in a hook to send JSON directly to
that client. It schedules a send and returns an asyncio task; async code may
await that task. Hook messages are sent before an automatically forwarded
model request. For a request made inside an async hook, await the send task
when its ordering relative to that request matters.
The client must still be connected: `on_close` runs after it disconnects.
JSON serialization errors are raised immediately and send failures are logged.

By default, messages containing `image` use the image example below; other
messages use `example_on_message`. Invalid requests and endpoint errors return
`{"error": "..."}`. If the prompt cannot be loaded, the proxy sends an error
and closes the connection.

## Building a request in the hook

For a minimal client message such as `{"myfield": "Value"}`, see
`example_on_message` in [chromites.py](./chromites.py). The example uses the
selected prompt's state and questions, adds the client value to the state, and
shows the model, state, questions, and optional images fields. Set `MODEL` in
`settings.py` to your loaded model ID.
Adapt these fields to the endpoint and your application; images, when used
with the local decision-model server, must be inline image data URLs.

`await self.request_model(payload)` waits for the endpoint's JSON result.
Modify `result` before `await self.to_client(result)` if needed. Returning
`None` tells the proxy the hook handled the message, so it does not make a
second model request or send a duplicate response. A hook can instead return
a request dict to use the default automatic forwarding. Invalid input and
model request errors are sent to the client as `{"error": "..."}`.

## Image examples

Open [index-image.html](./index-image.html), connect, choose a JPEG, PNG, or
WebP image, and send it. The browser reads the file as a base64 data URL and
sends `{"image": "data:image/...;base64,..."}` over the WebSocket.
`example_image_on_message` in [chromites.py](./chromites.py) adds it to the
selected prompt's request and sends the model result back. The WebSocket
message limit defaults to 64 MiB, including JSON and base64 encoding.

For prompts such as [woman.d.yaml](../prompts/woman.d.yaml), use the local
Transformers decision-model server, not the default LM Studio endpoint.
LM Studio's `/v1/systemone` accepts `choice`, `score`, and `noul` questions,
but rejects the prompt's `number`, `box`, and `boxes` types. Replacing those
types would change the requested answers rather than fix image inference.

Start the model server as described in the
[parent README](../readme.md#host-the-transformers-model). Then start the
proxy with the model host's address, for example:

```bash
python3 v6-decision-model/websocket-proxy/server.py \
  --base-url http://HOST_IP:8000
```

Use `127.0.0.1` instead of `HOST_IP` if both servers run on the same host.
Check `http://HOST_IP:8000/health` and wait for `model_loaded: true`, then
connect the image page to `ws://localhost:9999/woman/`. The `--base-url`
option overrides `LM_STUDIO_BASE_URL`; the WebSocket URL remains local to
the browser's machine.

For an image already on the proxy host, put `my-image.jpg` in an `images`
directory next to [chromites.py](./chromites.py), then use
`self.example_load_local_image()` inside a hook. It returns an inline data URL
that can be passed to `self.format_payload(images=[...])`. It reads relative
to the Python file, not the current working directory. Change the example path
in the method as needed; missing or unsupported files produce errors.

The proxy listens on localhost by default and has no authentication. It is a
local proof of concept, not a public-facing service; changing `HOST` can
expose it to other machines.
