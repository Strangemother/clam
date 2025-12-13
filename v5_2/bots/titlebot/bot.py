"""
file namer. - Or a better name "Title Bot" to receive text an create a short
title
"""
import pathlib
import os, sys, time

# sys.path.append(pathlib.Path(__file__).parent.absolute())

from clam.client import Client
from clam.toolclient import ToolClient
from clam.bot_pipe import (send_wait,
            print_content_response,
            print_payload_messages
        )


CLIENT_A_URL = "http://localhost:8010"


def main():
    client = FilenamerBot()
    client.start()


class FilenamerBot(ToolClient):
    port = 9394
    name = 'titlebot'

    def log(self, *a):
        print(f'[{self.get_name()}]', *map(str, a))


    def get_module_dir(self):
        """The template path root is this file location.
        """
        r = pathlib.Path(__file__).parent.absolute()
        # print('get_module_dir', r)
        return r

    def perform_work(self, message):
        """Memory sends a message to the llm, templated through the text file.
        The response is saved an a messsage is sent back to
        """
        self.log('start work')

        # text_out = self.get_rendered_template_message(message)
        text_out = self.template_rendered('titlebot.v2.txt',
            message=message,
            timestamp=time.time(),
            client_name=self.get_name(),
            port=self.port,
        )

        self.log("sending len:", len(text_out))
        d = send_wait(text_out)
        print_content_response(d)
        self.save_raw({
            'sent': text_out,
            'received': d

            })
        text = self.save_memory(d)

        # self.send_editor_message(
        #     user_message=message,
        #     bot_output=text,
        #     bot_prompt=text_out,
        # )

        return text

    def send_editor_message(self, **data_message):
        print('\n\nsend_editor_message\n')
        EDITOR_URL = "http://localhost:9387"
        t = self.send_message(EDITOR_URL, data_message)
        _id = t.get('id', None)
        if _id is not None:
            self.add_handler(_id, self.handle_send_editor_message, data_message)

    def handle_send_editor_message(self, data_message, resp):
        print('Editor message response')

    def save_raw(self, d):
        filename = f"raw/{d['received']['id']}-{d['received']['created']}.json"
        return self.save_json(filename, d)

    def save_memory(self, d):
        """Create a neater memory, for future callback as inline memory content text
        """
        text = self.easy_extract_message(d)
        if text is None:
            self.log('No memory for this')
            return

        filename = f"memory/{d['id']}-{d['created']}.txt"
        p = self.as_cache_path(filename)
        os.makedirs(p.parent, exist_ok=True)
        p.write_text(text)
        self.log(p)
        return text

    def easy_extract_message(self, d):
        return d['choices'][0]['message']['content']



if __name__ == "__main__":
    main()
