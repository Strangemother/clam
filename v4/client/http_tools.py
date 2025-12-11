"""

# Request
# curl http://localhost:11434/api/generate -d '{
#   "model": "llama3.2"
# }'


    url = "http://192.168.50.60:10000/api/generate/"
    r = await http_post_json(url, {'model': model_name})
"""
import requests
import json



def http_quick_get(url):
    headers = {
        'Content-Type': "application/json",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    print(' -- http_quick_get', url)
    # data = json.dumps(payload)
    response = requests.request("GET", url, headers=headers)
    return response


def http_post(url, d, reader=None, stream=True):
    headers = {
            'Content-Type': "application/json",
            'Cache-Control': "no-cache",
        }

    data = json.dumps(d)
    print('JSON POST', url)
    response = requests.request("POST", url,
        data=data, headers=headers, stream=stream)
    return response


def http_post_json(url, d, reader=None):
    rows = ()
    response = http_post_json(url, d, reader)
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
        if reader:
            reader(rl, response)
        rows += (rl,)
    return rows


def http_get_json(u):
    d = http_quick_get(u)
    return d.json()

