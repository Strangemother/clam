"""
Memorybpt - Running on port 9383
"""
import pathlib
from clam.toolclient import ToolClient
from clam.bot_pipe import (send_wait_message,
                      send_wait,
                      print_content_response,
                      make_message,
                      print_payload_messages)


CLIENT_A_URL = "http://localhost:8010"
FILENAMER_URL = "http://localhost:9394"


class MemoryBot(ToolClient):
    port = 9383
    name = 'memorybot'

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
        text_out = self.get_rendered_template_message(message,
                            template_name='memorybot.v2' )
        print("sending len:", len(text_out))
        msg = make_message(text_out)
        d = send_wait_message(msg)
        print_content_response(d)
        self.save_raw({
                'sent': msg,
                'received': d,
            })
        self.save_memory(d)
        text = self.easy_extract_message(d)
        return text

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
        return self.get_remote_filename(text, d)

    def save_memory_local(self, d):
        """Call to the llm directly through `get_filename` rather than
        the remote caller `save_memory`
        """
        filename = self.get_filename(text, d)
        result = self.template_rendered('save_memory.txt', {
                "text": text,
                "filename": filename
            })
        p = self.as_cache_path(filename)
        os.makedirs(p.parent, exist_ok=True)
        p.write_text(result)
        print("memory saved: ", p)
        return p

    def get_remote_filename(self, text, d, url=FILENAMER_URL):
        """Send a request to a remote machine with the remote receipt
        routine.
        """
        t = self.send_message(url, text)
        print('get_remote_filename: ', t)

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

