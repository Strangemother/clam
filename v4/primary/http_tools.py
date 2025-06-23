
import requests
import json



async def http_quick_get(url):
    headers = {
        'Content-Type': "application/json",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    print(' -- http_quick_get', url)
    # data = json.dumps(payload)
    response = requests.request("GET", url, headers=headers)
    return response


async def http_post_json(url, d, reader=None):
    headers = {
            'Content-Type': "application/json",
            'Cache-Control': "no-cache",
        }

    data = json.dumps(d)
    print('JSON POST', url)
    stream = True
    response = requests.request("POST", url, data=data,
                                headers=headers, stream=stream)
    rows = ()
    for line in response.iter_lines():
        # filter out keep-alive new lines
        if not line:
            continue
        decoded_line = line.decode('utf-8')
        rl = json.loads(decoded_line)
        if reader:
            reader(rl, response)
        rows += (rl,)
    return rows


async def http_get_json(u):
    d = await http_quick_get(u)
    return d.json()

