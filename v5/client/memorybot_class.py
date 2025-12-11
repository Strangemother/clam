"""
Memorybpt - Running on port 9383
"""
import pathlib

from client import Client
from toolclient import ToolClient

from bot_pipe import send_wait, print_content_response, print_payload_messages


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
        print(f'[{self.name}] start work')
        text_out = self.get_rendered_template_message(message)
        print("sending len:", len(text_out))
        d = send_wait(text_out)
        print_content_response(d)
        self.save_raw(d)
        self.save_memory(d)

    def save_raw(self, d):
        filename = f"raw/{d['id']}-{d['created']}.json"
        return self.save_json(filename, d)

    def save_memory(self, d):
        """Create a neater memory, for future callback as inline memory content text
        """


        text = self.easy_extract_message(d)
        if text is None:
            print('No memory for this')
            return

        filename = f"memory/{d['id']}-{d['created']}.txt"
        p = self.as_cache_path(filename)
        p.write_text(text)
        print("memory saved: ", p)
        return

    def easy_extract_message(self, d):
        return d['choices'][0]['message']['content']


if __name__ == "__main__":
    main()
