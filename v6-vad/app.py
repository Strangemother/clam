#!/usr/bin/env python3
"""Minimal browser microphone demo using Silero VAD."""

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

model = None
torch = None
get_speech_timestamps = None

@app.get("/")
def home():
    return render_template("index.html")


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Recording is too large."}), 413


@app.post("/vad")
def detect_speech():
    if model is None or torch is None or get_speech_timestamps is None:
        return jsonify({"error": "VAD model is not loaded."}), 503

    if request.headers.get("X-Sample-Rate") != "16000":
        return jsonify({"error": "Audio must be sampled at 16000 Hz."}), 400

    audio_bytes = request.get_data()
    if not audio_bytes or len(audio_bytes) % 2:
        return jsonify({"error": "Audio must contain 16-bit PCM samples."}), 400

    audio = torch.frombuffer(
        bytearray(audio_bytes),
        dtype=torch.int16,
    ).to(torch.float32) / 32768.0
    segments = get_speech_timestamps(
        audio,
        model,
        sampling_rate=16000,
        return_seconds=True,
    )

    print(f"VAD processed {len(audio) / 16000:.2f} seconds of audio.")
    if not segments:
        print("No speech detected.")
    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        print(
            f"Speech capture: {start:.2f}s to {end:.2f}s "
            f"({end - start:.2f}s)",
            flush=True,
        )

    return jsonify({"segments": segments})


def load_vad() -> None:
    global get_speech_timestamps, model, torch

    import torch as torch_module
    from silero_vad import get_speech_timestamps as timestamp_detector
    from silero_vad import load_silero_vad

    torch_module.set_num_threads(1)
    model = load_silero_vad()
    model.eval()
    torch = torch_module
    get_speech_timestamps = timestamp_detector
    print("Silero VAD model loaded on CPU.", flush=True)


if __name__ == "__main__":
    load_vad()
    app.run(host="127.0.0.1", port=9101, debug=True)
