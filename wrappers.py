from urllib.parse import urlparse
from pprint import pprint
import requests
import json


def main():

    host = "http://192.168.50.60"
    res = HTTPMsty(host=host, port=10001).example()

    return

    res = HTTPGradioStyleTTS2(host=host).example()
    print(res)

    res = HTTPGradioKokoro(host=host, port=50001).example()
    print(res)


def download_file(url, name=None):
    local_filename = url.split('/')[-1] if name is None else name
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk:
                f.write(chunk)
    return local_filename


class HTTPClient:
    port = 8000
    api_path = 'api'

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def clean_response(self, res):
        """
            https://www.gradio.app
                /guides/querying-gradio-apps-with-curl#step-2-get-the-result

        Here: event can be one of the following:

        + generating: indicating an intermediate result
        + complete: indicating that the prediction is complete and the final result
        + error: indicating that the prediction was not completed successfully
        + heartbeat: sent every 15 seconds to keep the request alive
        """
        text = res.text
        lines = text.strip().split('\n')
        print('Line count', len(lines))
        results = ()
        for index, line in enumerate(lines):
            dtype, data = line.split(':', 1)
            line_type = dtype.strip()

            if line_type == 'event':
                e_type = data.strip()
                # print('Event', e_type)
                # receive_complete
                self.next_receiver = getattr(self, f"receive_{e_type}")
                continue

            if line_type == 'data':
                res = self.next_receiver(data)
                results += (res, )
                self.next_receiver = None
                continue

            print('Unknown data type', line_type)
        return results
        # print(res.json())

    def _get(self, url):
        headers = {
            'Content-Type': "application/json",
            # 'Accept': "*/*",
            'Accept': "application/json",
            'Cache-Control': "no-cache",
            }

        # data = json.dumps(payload)
        print('get', url)
        response = requests.request("GET", url, headers=headers)
        return response

    def _post(self, url, payload):

        headers = {
            'Content-Type': "application/json",
            # 'Accept': "*/*",
            'Cache-Control': "no-cache",
            }

        data = json.dumps(payload)
        print('post', url)
        response = requests.request("POST", url, data=data, headers=headers)
        return response

    def example(self):

        url, payload = self.example_data()
        res = self._post(url, payload)
        print(res)
        ev = res.json().get('event_id', None)
        if ev is None:
            print('No event_id')
            print(res)
            return

        print('event_id', ev)

        l = f"{url}/{ev}"
        res = self._get(l)
        clean = self.clean_response(res)
        return clean

    def get_host_url(self):
        port = self.port
        host = self.host
        return f"{host}:{port}"

    def api_url(self, extra=''):
        """Return a url specific to the Gradio API
        """
        host = self.get_host_url()
        if extra.startswith('/'):
            extra = extra[1:]
        api_path = self.api_path
        return f"{host}/{api_path}/{extra}"

    def get_call_url(self, extra=''):
        if extra.startswith('/'):
            extra = extra[1:]

        url = f'call/{extra}'
        return self.api_url(url)


class HTTPMsty(HTTPClient):
    def get_call_url(self, extra=''):
        if extra.startswith('/'):
            extra = extra[1:]

        url = f'{extra}'
        return self.api_url(url)

    def example(self):
        prompt='Why is the sky blue?'
        print('= ', prompt)
        data = self.request_no_streaming(
            model='TinyDolphin',
            # model='phi4:latest',
            prompt=prompt,
        )
        response = data['response']
        print('\n', response)

    def prompt(self, text, **opts):
        default_model = 'phi4:latest'
        opts.setdefault('model', default_model)

        if opts['model'] is None:
            opts['model'] = 'phi4:latest'
        res = self.request_no_streaming(
            # 'model':'TinyDolphin',
            prompt=text,
            **opts,
        )
        response = res.get('response')
        if response is None:
            print("issues with response", response)
            response = 'no "response" attrib'
        return {
                'response': response
            }

    def request_no_streaming(self, **kw):
        # https://github.com/ollama/ollama/blob/main/docs/api.md#request-no-streaming
        url = self.get_call_url('generate')
        payload = {
            **kw,
            'stream': False,
        }
        resp = self._post(url, payload)
        data = resp.json()
        return data

    def get_model_list(self):
        url = self.get_call_url('tags')
        resp = self._get(url)
        data = resp.json()
        print('Models endpoint', url, resp)
        models = data['models']
        # names = set([x['name'] for x in models])
        for model in models:
            model['running'] = False # model['name'] in names
        return dict(models=models)

class HTTPJan(HTTPMsty):
    """Jan uses Cortex: http://192.168.50.60:9901/

    Once the application server has started, the host provides a fastapi
    resource.
    """
    # API Path for _jan_ is the root: http://192.168.50.60:9901/v1/models
    api_path = 'v1'

    def get_model_list(self):
        model_data = self.get_model_dict()

        models = ()
        for model in model_data['data']:
            item = {
                "name": model['name'],
                "model": model['model'],
            }
            models += (item, )
        return dict(
                models=models
            )

    def get_model_dict(self):
        ## OpenAI format:
        #https://platform.openai.com/docs/api-reference/models/list
        models = {}
        url = self.get_call_url('models')
        resp = self._get(url)
        # print('URL', url)
        return resp.json()
        # models = get_api_tags(name)
        # return models


class HTTPGradio(HTTPClient):
    port = 50000
    host = "http://127.0.0.1"
    api_path = 'gradio_api'

    def example_data(self):
        payload = { "data": [] }
        host = self.get_host_url()
        # url = f"{host}/gradio_api/call/gen_tts"
        url = self.api_url('/call/gen_tts')
        return payload, url

    def info(self):
        # host = self.get_host_url()
        # url = f"{host}/gradio_api/info"
        url = self.api_url('info')

    def get_file(self, row):
        """Returns the descriptor of the endpoint through a JSON GET

            http://192.168.50.60:50001/gradio_api/info

        """
        url = urlparse(row['url'])
        partial = '/gradio_api/'
        bits = url.path.split(partial)
        getfile = f"{url.scheme}://{url.netloc}{partial}{bits[1]}"
        print('getfile: ', getfile)
        download_file(getfile, name=row['orig_name'])
        row['fixed_url'] = getfile
        # http://192.168.50.60:50000/gradio_/gradio_api/file=...
        # http://192.168.50.60:50000/gradio_api/file=...
        return row

    def continue_event(self,url,  response):
        json_content = response.json()
        ev = json_content['event_id']
        l = f"{url}/{ev}"
        res = self._get(l)
        clean = self.clean_response(res)
        return clean[0]

    def receive_complete(self, content):
        """
        Called by the auto event chain when the _previous_ event line indicates
        'complete'
        """
        print('receive_complete')
        data = json.loads(content)
        pprint(data)
        res = {
            'files': (),
            'strings': (),
        }

        for row in data:
            pprint(row)
            if isinstance(row, dict):
                meta = row.get('meta', {})
                if meta.get('_type', None) == 'gradio.FileData':
                    print('Received file')
                    res['files'] += (self.get_file(row), )
                continue

            print('row is string')
            print(row)
            res['strings'] += (row, )

        return res

    def post_event_wait(self, url, payload):
        res = self._post(url, payload)
        print('post_event_wait response', res)

        if res.status_code != 200:
            print('Issue', res.reason)

        json_content = res.json()
        ev = json_content.get('event_id', None)
        print('json content', json_content)
        if ev is None:
            print('No event_id')
            print(res)
            return
        return res


class HTTPGradioKokoro(HTTPGradio):

    def prompt(self, text, **opts):
        return self.generate_tts(text)

    def generate_tts(self, text):
        url = self.get_call_url('process_input')
        payload = {
            "data": [
                text,
                "bf_emma",
            ]
        }

        res = self.post_event_wait(url, payload)
        # clean = self.clean_response(res)
        return self.continue_event(url, res)
        # return clean

        # print('event_id', ev)

        # l = f"{url}/{ev}"
        # res = self._get(l)
        # clean = self.clean_response(res)
        # return clean

    def example_data(self):
        payload = {
            "data": [
                "Speech generated using Kokoro through Gradio.",
                "bf_emma",
            ]
        }
        url = self.get_call_url('process_input')
        # url = "http://192.168.50.60:50000/gradio_api/call/process_input"
        return url, payload


class HTTPGradioParler(HTTPGradioKokoro):

    def generate_tts(self, text):
        url = self.get_call_url('process_input')
        payload = {
            "data": [
                text,
                "bf_emma",
            ]
        }

        res = self.post_event_wait(url, payload)
        return res

    def example_data(self):
        payload = {
            "data": [
                "Speech generated using Parler through Gradio.",
                "A 10 year old speaker with a child-like persona, a slightly faster-than-average pace in a confined space with very clear audio."
            ]
        }
        url = self.get_call_url('gen_tts')
        return url, payload


class HTTPGradioStyleTTS2(HTTPGradio):
    def prompt(self, text, **opts):
        return self.generate_tts(text)

    def generate_tts(self, text):
        url = self.get_call_url('on_generate_tts')
        payload = {
            "data": [
                text,
                "MAN MAN",
                120
            ]
        }

        res = self.post_event_wait(url, payload)
        return self.continue_event(url, res)

    def example_data(self):
        payload = {
            "data": [
                "Voice created using Style T T S, through Gradio.",
                "MAN MAN",
                # "English Lady",
                120
            ]
        }
        url = self.get_call_url('on_generate_tts')
        return url, payload


if __name__ == '__main__':
    main()