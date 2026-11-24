# v6

- https://huggingface.co/LiquidAI/d1-Omni-2B

## WebSocket proxy

See [websocket-proxy](./websocket-proxy/README.md) for a local WebSocket
client and transparent decision-model proxy.

## Ask the decision model through LM Studio

From the repository root, run [ask_lmstudio.py](./ask_lmstudio.py). It uses
Python 3's standard library and defaults to `http://192.168.50.60:1234`.

```bash
python3 v6/ask_lmstudio.py --list-models
python3 v6/ask_lmstudio.py YOUR_MODEL_ID
python3 v6/ask_lmstudio.py YOUR_MODEL_ID "Turn on the heater"
```

The script lists loaded decision model instance IDs from `/api/v1/models`
and asks questions through `/v1/systemone`. Without a question or context,
it routes "Turn on the light" to one of `lightbulb`, `heater`, or `door`.
Pass `--context "..."` to provide a different routing context. If no IDs are
listed, check that the decision model is loaded (not just downloaded) in the
Developer tab on the same LM Studio server. Use `--base-url` if that server
has a different address.

If authentication is enabled, set the `LM_STUDIO_API_TOKEN` environment
variable before running the script.

## Choose Chromite abilities

Run [ask_chromite.py](./ask_chromite.py) with an environment description,
a pet-owner message, or both:

```bash
python3 v6/ask_chromite.py --list-models
python3 v6/ask_chromite.py YOUR_MODEL_ID \
  --context "A quiet room with the pet resting nearby"
python3 v6/ask_chromite.py YOUR_MODEL_ID "The pet owner says hello"
python3 v6/ask_chromite.py YOUR_MODEL_ID \
  "The pet owner says hello" --context "A quiet room"
```

The script asks a yes/no probability question for each Chromite ability and
prints the selected abilities as a JSON list. Abilities with a probability
of at least `0.5` are selected. It uses the same server, authentication, and
model-list options as `ask_lmstudio.py`.

## Ask a YAML prompt repeatedly

From the repository root, run [first.py](./first.py) with a prompt file:

```bash
python3 v6/first.py v6/prompts/example.d.yaml --model d1-omni-2b
python3 v6/first.py v6/prompts/example.d.yaml --live-file
python3 v6/first.py v6/prompts/example.d.yaml --once
```

The prompt state is printed at startup. Press Enter to send the current
numbered example from the YAML file. Typed messages do not advance the example.
The selected example is echoed, and responses are printed as indented YAML
text. Ctrl+C exits; `--live-file` reloads the YAML file before each prompt,
and `--once` exits after one request.

For example, the invoice extraction prompt can be sent once by pressing
Enter to use its example message:

```bash
python3 v6/first.py v6/prompts/invoice.d.yaml --once
```

The support triage example can be run the same way:

```bash
python3 v6/first.py v6/prompts/support.d.yaml --once
```

## Ask once with an image

Run [second.py](./second.py) with the example image from the YAML file, or
override it with `--image` and a local JPEG, PNG, or WebP:

```bash
python3 v6/second.py v6/prompts/cats.d.yaml
python3 v6/second.py v6/prompts/cats.d.yaml --image ./scene.jpg
```

Without `--image`, the first item in `examples` supplies the image; its
optional `text` is included as image-description context. Relative image paths
in the YAML file are resolved relative to that file. The script sends the
prompt's `state` and `questions` with the image as an inline base64 data URL.
This uses only the Python standard library for image loading and encoding;
the configured model must support image input. `--model` and `--base-url`
can override the defaults.

## Host the Transformers model

To run the local model server and WebSocket proxy together on Windows,
double-click [run_server_and_ws.bat](./run_server_and_ws.bat). Alternatively,
run `python run_server_and_ws.py` with Python 3.10 through 3.14. The launcher
creates the shared `env/` and installs missing dependencies as needed. The
proxy forwards to the local model server (port 8430, or `D1_PORT` if set),
regardless of its configured remote endpoint.

The launcher skips servers already running or starting. It checks the model
health endpoint and the WebSocket handshake; another WebSocket service on the
configured port is indistinguishable from the proxy. Re-running it starts only
missing services. Keep each launcher window open: Ctrl+C or closing it stops
the servers started in that window, not servers it skipped. First model startup
can take time to download and load the model. Startup errors are printed.

Open `http://localhost:8430/` for links to the available pages and
browser-accessible endpoints.

With both servers running, open `http://localhost:8430/ws/ui/` for the
WebSocket text demo or `http://localhost:8430/ws/images-ui` for the image
demo. These Flask templates are separate copies of the standalone proxy pages
and share CSS and JavaScript in `static/`. Replace `8430` with `D1_PORT` if
configured. The pages default to
`ws://localhost:9999/chromite/`; edit that address if the proxy uses another
host, port, or prompt. By default the proxy is accessible only on the same
machine as the browser.

On the Windows host with an RTX 5060, run:

```powershell
cd C:\dev\clam\v6
python easy-run.py
```

`easy-run.py` runs [first-setup.py](./first-setup.py), which creates `env/`
and installs [requirements.txt](./requirements.txt), then starts
[server.py](./server.py). The Flask server loads `LiquidAI/d1-Omni-2B` and
provides `/v1/systemone` and `/api/v1/models` on port 8000. First startup
downloads the model. Allow inbound TCP port 8000 through Windows Firewall.

Open `http://HOST_IP:8000/ui` to use the browser prompt runner. The page lets
you select a YAML prompt, edit its state, enter a user message or choose an
example, and choose between the local Transformers model and LM Studio.
The **Prompt YAML** tab shows the selected prompt file's source. For image
examples, drop a PNG, JPEG, or WebP onto the image area to override the YAML
image. The page also has a dark-mode toggle and a copyable Python request
example. Dropdowns start unselected so a prompt, backend, and any required
model or example must be selected explicitly.
In the YAML tab, edit the source and choose **Save changes** to overwrite the
selected prompt, or provide a new `*.d.yaml` filename and choose **Save as
new**. The server validates the prompt structure before writing and refuses
to overwrite an existing file when saving as new.

The browser UI serves Vue 3's prebuilt global browser script from
`v6/static/vue.global.prod.js`. No Node.js, npm, build step, or browser
internet access is required. The Vue MIT license is included at
`v6/static/VUE-LICENSE.txt`.

When a local-model image example is selected, the UI displays the image.
After inference, normalized `box` and `boxes` answers are drawn as an SVG
overlay on that image. A dropped override is shown and annotated instead.

The LM Studio option uses the endpoint `http://192.168.50.60:1234` by default.
Set another endpoint at launch with `--lm-studio-url` or the
`LM_STUDIO_BASE_URL` environment variable:

```powershell
python easy-run.py --lm-studio-url http://HOST_IP:1234
```

The browser fetches loaded decision-model IDs from LM Studio. LM Studio mode
supports text inputs and `noul`, `choice`, and `score` questions; image inputs
and other question types require the local Transformers model. If the LM Studio
server requires authentication, set `LM_STUDIO_API_TOKEN` on the host running
this service.

On the client, point `second.py` at the host's LAN address:

```powershell
python second.py prompts\cats.d.yaml --image .\prompts\cats.png `
  --base-url http://HOST_IP:8000 --model d1-omni-2b
```

This demo service has no authentication; keep it on a trusted network.

### The routing request sent to LM Studio

```bash
curl --fail-with-body http://192.168.50.60:1234/v1/systemone \
  -H "Content-Type: application/json" -d '{
  "model": "YOUR_MODEL_ID",
  "state": "Select from one of these internal routes: lightbulb, heater, door.",
  "questions": {
    "route": {
      "type": "choice",
      "instructions": "Turn on the light",
      "criteria": {
        "lightbulb": "Control the lights",
        "heater": "Control the heating",
        "door": "Control the door"
      }
    }
  }
}'
```

The response contains the selected route in `answers.route`. If
authentication is enabled, add an `Authorization: Bearer <token>` header.
