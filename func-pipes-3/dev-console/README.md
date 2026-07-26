# Func Pipes Dev Backend

This is an independent fake backend for exercising the `func-pipes-3` browser
client. It serves a browser console and a WebSocket server from one process.
Every message is broadcast to all connected clients, including the sender.

## Run

```bash
cd /workspaces/clam/func-pipes-3
python -m pip install -r dev-console/requirements.txt
python dev-console/server.py
```

Open http://127.0.0.1:8001/ in one browser tab, then set the `func-pipes-3`
socket URL to `ws://127.0.0.1:8778/` and connect. Messages sent from either
page will appear in both traffic logs.

Use `--http-port`, `--ws-port`, and `--host` to change the defaults.