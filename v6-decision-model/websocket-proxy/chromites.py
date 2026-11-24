"""Per-connection Chromite hooks and prompt loading."""

import asyncio
import json
import logging
from pathlib import Path
import re
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from prompt_utils import load_prompt


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
logger = logging.getLogger(__name__)


class Chromite:
    def __init__(self, client, path):
        self.client = client
        self.path = path
        match = re.fullmatch(r"/([A-Za-z0-9][A-Za-z0-9_-]*)/?", path)
        if not match:
            raise ValueError("Path must be /<prompt-name> or /<prompt-name>/")

        self.prompt_path = (PROMPTS_DIR / f"{match.group(1)}.d.yaml").resolve()
        if self.prompt_path.parent != PROMPTS_DIR.resolve():
            raise ValueError("Prompt must be in the prompts directory.")
        self.prompt = load_prompt(self.prompt_path, allow_image_examples=True)
        self._client_send_lock = asyncio.Lock()
        self._client_sends = set()

    def to_client(self, message):
        """Schedule a JSON message to this client and return its send task.

        Call from a hook as self.to_client({...}); the server waits for hook
        messages before forwarding the model request. The client must still
        be connected. Serialization errors are raised immediately, and send
        failures are logged. Async callers may also await the returned task.
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

    def on_create(self):
        pass

    def on_message(self, message):
        """Prepare a client message for the decision-model endpoint.

        message is a dict parsed from the client's JSON. Return a dict to
        forward to the model, not directly to the client. The model's
        response is sent back to the client.
        """
        return message

    def on_close(self):
        pass
