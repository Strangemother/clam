"""A Client connects to the "primary" as a message unit.
It can send and receive messages as a client.

In this version, this acts as a normaliser for communication to a host.
Each "conversation" is its own stack.

"""

import asyncio
from loguru import logger
import json


from flask import Flask

app = Flask(__name__)

from flask import render_template

from http_tools import http_quick_get, http_post_json, http_post


LM_STUDIO_ENDPOINT = "http://192.168.50.60:1234"
LM_STUDIO_MODELS = "/v1/models/"
LM_STUDIO_CHAT_COMPLETIONS = "/v1/chat/completions/"

DEFAULT_MODEL_NAME = 'unsloth/gpt-oss-20b' # data selected at http://localhost:9876/models

OLLOMA_ENDPOINT = "http://192.168.50.60:10000"
OLLOMA_CHAT_ENDPOINT = "/api/chat/"
OLLOMA_TAGS_ENDPOINT = "/api/tags/"
OLLOMA_PS_ENDPOINT = "/api/ps/"
OLLOMA_GENERATE_ENDPOINT = "/api/generate/"

JAN_ENDPOINT = "http://192.168.50.60:9901"
JAN_MODELS = "/v1/models" # Note Jan models end slash (fails if exists without a model name)


class RequestBase:
    host = None
    unit_class = None

    def __init__(self, **kw):
        self.__dict__.update(kw)


    def get_endpoint(self):
        return self.host


    def clean_models(self, data):
        return data

    def get_models(self):
        h = self.get_endpoint()
        data = http_quick_get(h + self.get_models_endpoint()).json()
        return self.clean_models(data)

    def get_target_model(self):
        return DEFAULT_MODEL_NAME

    def chat_completions(self, data, reader=None):
        h = self.get_endpoint()
        url = h + self.get_chat_completions_endpoint()
        resp = http_post(url, data, reader)
        return resp

        # rows = http_post_json(url, data, reader)
        # if data['stream'] is False:
        #     return json.loads("".join(rows))
        # return rows


class Olloma(RequestBase):
    # def get_endpoint(self):
    #     return OLLOMA_ENDPOINT

    def get_models_endpoint(self):
        return OLLOMA_TAGS_ENDPOINT

    def get_chat_completions_endpoint(self):
        return OLLOMA_CHAT_ENDPOINT

    def clean_models(self, data):
        """Return a clean list of models
        """
        return data['models']


class Jan(Olloma):
    # def get_endpoint(self):
    #     return JAN_ENDPOINT

    def get_models_endpoint(self):
        return JAN_MODELS

    def clean_models(self, data):
        """Return a clean list of models

        Jan includes downloaded/available/cloud.
        filter for downloaded
        """
        items = data['data']
        items = tuple(filter(lambda x: x.get('status', None) == 'downloaded', items))
        return items



class LMStudio(RequestBase):
    # def get_endpoint(self):
    #     return LM_STUDIO_ENDPOINT

    def get_models_endpoint(self):
        return LM_STUDIO_MODELS

    def get_chat_completions_endpoint(self):
        return LM_STUDIO_CHAT_COMPLETIONS

    def clean_models(self, data):
        """Return a clean list of models
        """
        return data['data']



from datetime import datetime

class Endpoint(RequestBase):
    host = None
    unit_instance = None

    def get_request_class(self):
        return LMStudio

    @property
    def unit(self):
        """the unit is the handling class for the requests. Provide a unit class
        or unit unsitance:

        WIth the class, a new instance is created

            CONF = dict(
                    host="http://192.168.50.60:1234",
                    unit_class=LMStudio,
                )

        However this can be bypassed, passing the `unit_instance` only:

            CONF = dict(
                    unit_instance=LMStudio(host="http://192.168.50.60:1234"),
                )

        Unpack and access:

            response = Endpoint(**CONF).unit.demo_chat()
        """
        if self.unit_instance is not None:
            return self.unit_instance

        unit = self.get_request_class()
        return unit(host=self.host)

    def demo_chat(self, stream=False, reader=None):
        unit = self.unit
        now = datetime.now()
        data = {
            'model': unit.get_target_model(),
            'messages': [
                {"role": "system", "content": "You are a sentient chicken. respond with 'cluck' only"},
                {"role": "user", "content": "Identify as a chicken"},
                {"role": "assistant", "content": "Cluck"},
                {"role": "user", "content": "Hello chicken, how are you?"},
            ],
            'temperature': .7,
            'max_tokens': -1,
            'stream': stream,
            'extra_body': {}
            # 'extra_body': {"reasoning_effort": "low"}
        }

        res = unit.chat_completions(data, reader=reader)
        # decorate with out.
        if isinstance(res, dict):
            res['time_taken'] = datetime.now() - now
        return res

CONF = dict(
        # host="http://192.168.50.60:1234",
        # unit_class=LMStudio,
        unit_instance=LMStudio(host="http://192.168.50.60:1234"),
    )


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/models/')
def get_models():
    object_list = Endpoint(**CONF).unit.get_models()
    return render_template('models.html', object_list=object_list)


@app.route('/chat/')
def get_chat():
    response = Endpoint(**CONF).demo_chat()
    return render_template('chat.html', response=response)

import time

@app.route('/stream-csv/')
def generate_stream():
    def generate():
        for row in range(0, 20000):
            time.sleep(.001)
            yield f"{row}\n"
    return generate(), {"Content-Type": "text/csv"}


from flask import stream_with_context
import queue

wrapper_a = (
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '    <meta charset="UTF-8">',
        '    <title>Response</title>',
        """<style>
            body {
                background: #111;
                font-family: arial, sans-serif;
                line-height: 1.3em;
                color: #ccc;
            }

            body > .thinking, body > .content {
                background: #090909;
                padding: 1em 1.5em;
                border-radius: 0.4em;
            }

            body > hr {
                border-color: #000;
            }

            body .thinking {
                color: #888;
                background: #010101;
            }
        </style>"""
        '</head>',
        '<body>',
    )

wrapper_b = (
        '</body>',
        '</html>',
    )


@app.route('/stream/')
def streamed_response():

    lines = queue.Queue()

    def generate():
        for line in wrapper_a:
            yield f'{line}\n'

        time.sleep(.01)

        response = Endpoint(**CONF).demo_chat(stream=True)

        thinking = True
        yield '<div class="thinking">\n'

        for line in response.iter_lines():
            # filter out keep-alive new lines
            if not line:
                continue

            decoded_line = line.decode('utf-8')
            try:
                if decoded_line.startswith('data:'):
                    decoded_line = decoded_line[len('data: '):]
                rl = json.loads(decoded_line)
            except json.decoder.JSONDecodeError:
                print('Response is not JSON', decoded_line)
                rl = decoded_line
            # lines.put_nowait(rl)
            item = rl

            if item == '[DONE]':
                print('[DONE]')
                break

            if item:
                # We want to stream the text response only.
                value =''
                delta = item['choices'][0]['delta']
                if 'reasoning' in delta:
                    value = delta['reasoning']
                else:
                    if thinking is True:
                        thinking = False
                        yield '</div>\n'
                        yield '\n\n<hr>\n\n' # visible split for now
                        yield '<div class="content">\n'

                if 'content' in delta:
                    value = delta['content']
                yield value

            time.sleep(.001)

        yield '</div>\n'
        for line in wrapper_b:
            yield f'{line}\n'

    return generate()#, {"Content-Type": "text/plain"}


if __name__ == '__main__':
    app.run(host='localhost', port=9876, debug=True,threaded=True)