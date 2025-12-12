"""
This serves as an example of the available methods on a client.
"""
import pathlib
import os

from client import Client
from toolclient import ToolClient

from bot_pipe import (send_wait_message,
                      send_wait,
                      print_content_response,
                      make_message,
                      print_payload_messages)


CLIENT_A_URL = "http://localhost:8010"
FILENAMER_URL = "http://localhost:9394"


def main():
    client = MemoryBot(
                    # port=MY_PORT,
                    # name=NAME,
                    # auto_start=5,
                    # on_start=start_process
                )
    client.start()


class MemoryBot(ToolClient):
    port = 9383
    name = 'memorybot'

    def perform_work(self, message):
        """Memory sends a message to the llm, templated through the text file.
        The response is saved an a messsage is sent back to
        """

        text_out = self.get_rendered_template_message(message)
        msg = make_message(text_out)
        d = send_wait_message(msg)
        print_content_response(d)
        self.save_raw({
                'sent': msg,
                'received': d,
            })
        self.save_memory(d)

    def save_raw(self, d):
        """Save a raw JSON File of message and response."""
        filename = f"raw/{d['received']['id']}-{d['received']['created']}.json"
        return self.save_json(filename, d)

    def save_memory(self, d):
        """Create a neater memory, for future callback as inline memory content text
        """
        text = self.easy_extract_message(d)
        if text is None:
            print('No memory for this')
            return
        return self.remote_flow_example(text, d)

    def remote_flow_example(self, text, d, url=FILENAMER_URL):
        """Send a request to a remote machine with the remote receipt
        routine.
        """
        t = self.send_message(url, text)
        print('remote_flow_example: ', t)
        _id = t.get('id', None)
        if _id is not None:
            self.add_handler(_id, self.on_get_remote_filename, text, d)

    def on_get_remote_filename(self, text, d, resp):
        """Called through the receipt response caller
        to continue the _remote_filename_
        """
        print('\non_get_remote_filename')
        print('  ? text', text)
        result = resp['message']
        print('  < resp', result)

        name = result[0:50].replace(' ', '-').replace("'", '')
        filename = f"memory/{name}-{d['created']}.txt"

        result = self.template_rendered('save_memory.txt', {
                "text": text,
                "filename": filename
            })

        p = self.as_safe_cache_path(filename)
        p.write_text(result)
        print("memory saved: ", p)

    def get_filename(self, text, d):
        """Send a templated request to the LLM, waiting for the
        input and returning a formatted filename.
        """
        result = self.template_rendered('title_request.txt', {
                    "text": text,
                })

        resp = send_wait(result)
        resp_text = self.easy_extract_message(resp)
        filename = f"memory/{d['id']}-{d['created']}.txt"
        if resp_text:
            name = resp_text[0:50].replace(' ', '-').replace("'", '')
            filename = f"memory/{name}-{d['created']}.txt"
        return filename

    def easy_extract_message(self, d):
        return d['choices'][0]['message']['content']


if __name__ == "__main__":
    main()
