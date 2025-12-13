import pathlib, os
from clam.toolclient import ToolClient
from clam.bot_pipe import (send_wait_message,
                      send_wait,
                      print_content_response,
                      make_message,
                      print_payload_messages)


CLIENT_A_URL = "http://localhost:8010"
FILENAMER_URL = "http://localhost:9394"


class Bot(ToolClient):
    port = 9390
    name = 'selector'

    def get_module_dir(self):
        """The template path root is this file location.
        """
        r = pathlib.Path(__file__).parent.absolute().as_posix()
        # print('get_module_dir', r)
        return r

    def perform_work(self, message):
        """Memory sends a message to the llm, templated through the text file.
        The response is saved an a messsage is sent back to
        """
        print(f'[{self.get_name()}] start work')
        # text_out = self.get_rendered_template_message(message,
        #                     # template_name='memorybot.v2'
        #                     )

        text_out = Prompt("model-selector.v2.prompt.md").render(
                    message=message,
                    timestamp=time.time(),
                    client_name=self.get_name(),
                    port=self.port,
                )
        # text_out = self.template_rendered("model-selector.v2.prompt.md",
        #     message=message,
        #     timestamp=time.time(),
        #     client_name=self.get_name(),
        #     port=self.port,
        # )
        print("sending len:", len(text_out))
        msg = make_message(text_out)
        d = send_wait_message(msg)
        print_content_response(d)
        self.save_raw({
                'sent': msg,
                'received': d,
            })
        self.save_memory(d)

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

        return text

    def easy_extract_message(self, d):
        return d['choices'][0]['message']['content']

