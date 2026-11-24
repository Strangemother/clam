"""Per-connection Chromite hooks and prompt loading."""

import asyncio
import json
import logging
from pathlib import Path
import re
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from prompt_utils import load_prompt
from second import image_data_url
from tools import make_headers, request_json
import settings


PROMPTS_DIR = settings.PROMPTS_DIR
logger = logging.getLogger(__name__)


class Chromite:
    live_prompt = settings.LIVE_PROMPT

    def __init__(self, client, path):
        self.client = client
        self.path = path
        self.base_url = None
        match = re.fullmatch(r"/([A-Za-z0-9][A-Za-z0-9_-]*)/?", path)
        if not match:
            raise ValueError("Path must be /<prompt-name> or /<prompt-name>/")
        self.matched_path = match.group(1)
        
        self.prompt = None
        self.load_prompt()
        self._client_send_lock = asyncio.Lock()
        self._client_sends = set()

    def load_prompt(self):
        self.prompt_path = (PROMPTS_DIR / f"{self.matched_path}.d.yaml").resolve()
        if self.prompt_path.parent != PROMPTS_DIR.resolve():
            raise ValueError("Prompt must be in the prompts directory.")
        self.prompt = load_prompt(self.prompt_path, allow_image_examples=True)

    def to_client(self, message):
        """Schedule a JSON message to this client and return its send task.

        Call from a hook as self.to_client({...}). The client must still be
        connected. Serialization errors are raised immediately, and send
        failures are logged. Async callers may await the returned task.
        """
        data = json.dumps(message)
        task = asyncio.create_task(self._send_to_client(data))
        self._client_sends.add(task)
        task.add_done_callback(self._client_send_done)
        return task

    async def _send_to_client(self, data):
        async with self._client_send_lock:
            await self.client.send(data)

    def _client_send_done(self, task):
        self._client_sends.discard(task)
        if not task.cancelled():
            error = task.exception()
            if error is not None:
                logger.error(
                    "Could not send message to client: %s", error,
                    exc_info=(type(error), error, error.__traceback__),
                )

    async def _flush_client_sends(self):
        if self._client_sends:
            await asyncio.gather(*self._client_sends)

    async def request_model(self, payload):
        """Send a decision request and wait for its JSON response."""
        if self.base_url is None:
            raise RuntimeError("Decision-model base URL is not configured.")
        return await asyncio.to_thread(
            request_json,
            f"{self.base_url}/v1/systemone",
            make_headers(),
            payload,
        )

    def on_create(self):
        pass

    async def on_message(self, message):
        """Prepare a client message for the decision-model endpoint.

        Return a dict to forward automatically, or None after handling the
        message yourself. This hook can also be async; see the example below.
        """

        if "image" in message:
            return await self.example_image_on_message(message)
        if "state" in message:
            if not isinstance(message["state"], str):
                raise ValueError("'state' must be a string.")
            return await self.example_on_message({"myfield": message["state"]})
        return await self.example_on_message(message)

    def example_load_local_image(self):
        """Load an image relative to this file as an inline data URL."""
        try:
            return image_data_url(
                "./images/my-image.jpg", Path(__file__).resolve().parent
            )
        except OSError as exc:
            raise RuntimeError(f"Could not load local image: {exc}") from exc

    async def example_image_on_message(self, message):
        """Send an image received from the browser to the model."""
        image = message.get("image")
        if not isinstance(image, str) or not image.startswith("data:image/"):
            raise ValueError("'image' must be an inline image data URL.")
        if self.live_prompt:
            self.load_prompt()
        payload = self.format_payload(images=[image])
        result = await self.request_model(payload)
        await self.to_client(result)
        return None

    async def example_on_message(self, message):
        """Example: build a request, await the result, and send it yourself."""
        print('Example on_message')
        
        if self.live_prompt:
            self.load_prompt()
        
        value = message.get("myfield")

        state = f"{self.prompt['state']}\n\nClient message: {value}"
        payload = self.format_payload(state=state)
        print('Payload ready:\n', payload)
        await self.to_client(payload)
        result = await self.request_model(payload)
        await self.to_client(result)
        return None

    def format_payload(self, state=None, questions=None, images=None):
        return {
            "model": settings.MODEL,
            "state": state or self.prompt['state'],
            "questions": questions or self.prompt["questions"],
            "images": images or [],
        }
    
    def on_close(self):
        pass
