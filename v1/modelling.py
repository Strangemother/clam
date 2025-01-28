import json
from pathlib import Path
from math import log
import requests

HERE = Path(__file__).parent
DATA_PATH = HERE / 'data/'


def quick_get(url):
    headers = {
        'Content-Type': "application/json",
        'Accept': "*/*",
        'Cache-Control': "no-cache",
        }

    # data = json.dumps(payload)
    response = requests.request("GET", url, headers=headers)
    return response


def quick_post(url):
    payload = {
                "data": [
                        "'This is the best time of my life, Bartley,' she said happily.",
                        "A 10 year old speaker with a child-like persona, a slightly faster-than-average pace in a confined space with very clear audio."
                    ]
            }

    headers = {
        'Content-Type': "application/json",
        # 'Accept': "*/*",
        'Cache-Control': "no-cache",
        }


    url = "http://192.168.50.60:50000/gradio_api/call/gen_tts"

    data = json.dumps(payload)
    response = requests.request("GET", url, data=data, headers=headers)
    return response


def get_data_file(filename):
    """
    Read the filepath relative to the DATA location.
    Return a resolved JSON dict.
    """
    dp = DATA_PATH / filename
    if dp.exists() is False:
        raise Exception('Data filepath does not exist')

    return json.loads(dp.read_text())


def prettier_size(n,pow=0,b=1024,u='B',pre=['']+[p+'i'for p in'KMGTPEZY']):
    r,f=min(int(log(max(n*b**pow,1),b)),len(pre)-1),'{:,.%if} %s%s'
    return (f%(abs(r%(-r-1)),pre[r],u)).format(n*b**pow/b**float(r))


def pretty_size(n,pow=0,b=1024,u='B',pre=['']+[p+'i'for p in'KMGTPEZY']):
    pow,n=min(int(log(max(n*b**pow,1),b)),len(pre)-1),n*b**pow
    return "%%.%if %%s%%s"%abs(pow%(-pow-1))%(n/b**float(pow),pre[pow],u)


def get_services():
    """Read and return the service JSON
    """
    return get_data_file('services.json')


def get_services_dict():
    # [name]
    res = {}
    for item in get_services()['items']:
        res[item['name']] = item
    return res


def get_api_tags(name):
    obj = get_services_dict()[name]
    uri = "api/tags"
    u = f"{obj['url']}/{uri}"
    return quick_get(u).json()


def get_service_object(name):
    obj = get_services_dict()[name]
    return obj


def get_api_ps(name):
    obj = get_service_object(name)
    uri = "api/ps"
    u = f"{obj['url']}/{uri}"
    return quick_get(u).json()


def clean_models(models):
    res = ()
    for model in models['models']:
        detail = model['details']
        r = dict(
                name=model['name'],
                # model=model['model'],
                size=prettier_size(model['size'], u='b', b=1000, pre=['','k','m','g']),
                # size=model['size'] * 1.e-6, # to meg.
                # family=detail['family'],
                parameter_size=detail['parameter_size'],
            )
        res += (r, )
    return { "models": res}


if __name__ == '__main__':
    main()