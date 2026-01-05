

## Getting Started

You can communicate to a bot through the `clam` command. First start a backbone

    # config.py
    clam backbone
    # Starting backbone service on 127.0.0.1:5000

Now you can build a client to connect to the backbone, or run the terminal cli on a prompt.

In the same directory, start a new shell. Point to your prompt file

    clam cli -f prompt/chicken.prompt.md
    # same as
    clam cli chicken

---

A client is actually a flask website, that orchestrates with with the backbone. Here's a full example:

```py
from orchestra.client import Client
import time
import argparse


class EchoClient(Client):
    def process_job(self, job):
        n = self.kwargs.get('name', self.__class__.__name__)
        print(f"[{n}] Got job: {job}")
        time.sleep(2)
        return job


parser = argparse.ArgumentParser(description="Clam Client")
parser.add_argument('--id', default=None, type=str)
parser.add_argument('--name', default=None, type=str)
parser.add_argument('--port', default=0, type=int)
ns, unknown = parser.parse_known_args()


if __name__ == '__main__':
    EchoClient(
        port=ns.port,
        backbone_url='http://localhost:5000/',
        id=ns.id,
        name=ns.name,
    ).run()
```

Register on the backbone graph:

    python orchestra\example\chat.py --prompt announcer --name announcer
