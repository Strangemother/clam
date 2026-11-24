# Decision-model WebSocket proxy

On Windows, double-click [run.bat](./run.bat). It uses the parent `env/`,
creating it and installing the proxy dependencies if needed.

Alternatively, install the proxy dependencies and start it manually:

```bash
python3 -m pip install -r v6-decision-model/websocket-proxy/requirements.txt
python3 v6-decision-model/websocket-proxy/server.py \
  --base-url http://127.0.0.1:8000
```

Set `--base-url` to the HTTP server hosting the decision model. It defaults to
`LM_STUDIO_BASE_URL`, or `http://192.168.50.60:1234` if unset. If LM Studio
requires authentication, set `LM_STUDIO_API_TOKEN` on the proxy host.

Open [index.html](./index.html) in a browser on the same machine and connect to
`ws://localhost:9999/chromite/`. The page supports light and dark modes. Replace
`YOUR_MODEL_ID` with a loaded model ID and send the JSON request.

The connection path selects a prompt in `../prompts/`: for example,
`/chromite-3` or `/chromite-3/` loads `chromite-3.d.yaml`. The file must
already exist. Each connection creates a separate `Chromite` instance in
[chromites.py](./chromites.py), with `client`, `path`, `prompt_path`, and
the loaded `prompt` available to its `on_create`, `on_message`, and `on_close`
hooks. `on_message` receives a JSON object and returns the object to forward.
The hooks are synchronous and can be extended for per-connection state.
Call `self.to_client({"event": "ready"})` in a hook to send JSON directly to
that client. It schedules a send and returns an asyncio task; async code may
await that task. Hook messages are sent before the model request is forwarded.
The client must still be connected: `on_close` runs after it disconnects.
JSON serialization errors are raised immediately and send failures are logged.

Each message must be a complete JSON object accepted by the HTTP server's
`/v1/systemone` endpoint. The prompt is loaded for your extensions but is not
automatically applied to the request. The proxy forwards the request unchanged
and returns the endpoint's JSON response. Invalid requests and endpoint errors
return `{"error": "..."}`. If the prompt cannot be loaded, the proxy sends an
error and closes the connection.

The proxy listens on localhost only and has no authentication. It is a local
proof of concept, not a public-facing service.
