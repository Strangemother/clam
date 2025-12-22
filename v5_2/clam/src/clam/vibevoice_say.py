import asyncio
import urllib.parse
import threading
import time
import json

import websockets
import sounddevice as sd

BASE_URL = "ws://192.168.50.60:42003"
TEXT = "I think I’ll meet julie tomorrow\nin the park about 3pm."
# TEXT = "You're an idiot for even asking that stupid question. Now leave me the fuck alone."
SAMPLE_RATE = 24000
CHANNELS = 1
VOICE_PRESETS = {
    "klara": {
        "voice": "de-Spk1_woman",
        "cfg": 2.0,
        "step": 5
    },
    "emma": {
        "voice": "en-Emma_woman",
        "cfg": 2.8,
        "step": 20
    },
    "dutch": {
        "voice": "nl-Spk1_woman",
        "cfg": 2.5,
        "step": 5
    },
    "italian": {
        "voice": "it-Spk0_woman",
        "cfg": 2.9,
        "step": 15
    },
    "german": {
        "voice": "de-Spk0_man",
        "cfg": 2.50,
        "step": 13
    }
}

class PCMPlayer:
    def __init__(self, samplerate=24000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._stream = None

    def start(self):
        if self._stream:
            return

        def callback(outdata, frames, time_info, status):
            needed = frames * self.channels * 2  # bytes (int16)
            with self._lock:
                if len(self._buf) >= needed:
                    chunk = self._buf[:needed]
                    del self._buf[:needed]
                else:
                    chunk = bytes(self._buf)
                    self._buf.clear()
                    chunk += b"\x00" * (needed - len(chunk))

            outdata[:] = chunk

        self._stream = sd.RawOutputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="int16",
            callback=callback,
            blocksize=0,
        )
        self._stream.start()

    def push(self, pcm_bytes: bytes):
        if not pcm_bytes:
            return
        with self._lock:
            self._buf.extend(pcm_bytes)

    def buffered_seconds(self) -> float:
        with self._lock:
            nbytes = len(self._buf)
        bytes_per_second = self.samplerate * self.channels * 2
        return nbytes / bytes_per_second

    async def drain(self, poll=0.02, extra_tail=0.1):
        """
        Wait until queued audio is played.
        extra_tail accounts for audio already handed to PortAudio.
        """
        while self.buffered_seconds() > 0:
            await asyncio.sleep(poll)
        await asyncio.sleep(extra_tail)

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            self._buf.clear()



def async_run(text, debug=False):

    try:
        asyncio.run(main(text, debug=debug))
    except KeyboardInterrupt:
        pass

async def main(text, debug=False):
    player = PCMPlayer(samplerate=SAMPLE_RATE, channels=CHANNELS)
    player.start()

    # Default settings
    voice = "de-Spk0_man"
    cfg = 2.50
    step = 15

    # Try to parse as JSON to get settings
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            # Load preset if name is specified
            preset_name = data.get('name', '').lower()
            if preset_name in VOICE_PRESETS:
                preset = VOICE_PRESETS[preset_name]
                voice = preset.get('voice', voice)
                cfg = preset.get('cfg', cfg)
                step = preset.get('step', step)

            # Extract text and allow individual settings to override preset
            text = data.get('text', text)
            voice = data.get('voice', voice)
            cfg = data.get('cfg', cfg)
            step = data.get('step', step)
    except (json.JSONDecodeError, TypeError):
        # Not JSON, treat as plain text
        pass

    uri = (f"{BASE_URL}/stream?"
            f"voice={voice}"
            f"&cfg={cfg}"
            f"&step={step}"
            f"&text={urllib.parse.quote(text)}")
    async with websockets.connect(uri) as ws:
        async for message in ws:
            if isinstance(message, (bytes, bytearray)):
                player.push(message)
            else:
                if debug:
                    print("log:", message)
    # 👇 key bit: let the buffer finish playing before exit
    await player.drain(extra_tail=0.3)  # Increased to avoid cutting off the end
    player.stop()


if __name__ == "__main__":
    async_run(TEXT)

