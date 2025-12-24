
import requests

url = 'http://127.0.0.1:9202/job'

res = requests.post(url,
        data=bytes('post some bytes', 'utf'),
        timeout=3,
        # headers=headers
    )


print(res.text)