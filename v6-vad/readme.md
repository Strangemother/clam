# Minimal Silero VAD demo

This proof of concept uses [Silero VAD](https://github.com/snakers4/silero-vad)
to detect speech from your browser microphone. The browser records while
**Listen** is active; selecting **Stop and detect** sends the recording to
Flask, and detected speech start/end times are printed in the server terminal.

## Run

```bash
python -m venv .venv
```

Activate the virtual environment, then install and start the app:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The Silero model is
loaded on startup and runs on CPU. The first startup may download the model.
Allow microphone access when the browser asks.

This is a local proof of concept, not a production server. The microphone
capture API requires a secure browser context; `localhost` is supported.

The page markup is in `templates/index.html`; styling and browser capture
logic are in `static/vad.css` and `static/vad.js`.
