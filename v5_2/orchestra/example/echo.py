"""Example client that echoes jobs back."""
from orchestra.client import Client
import time
import argparse


class EchoClient(Client):
    def process_job(self, job):
        n = self.kwargs.get('name', self.__class__.__name__)
        print(f"[{n}] Got job: {job}")
        # time.sleep(2)
        # return bytes("I like butterscotch.", 'utf-8')
        # return str({'echo': job})
        # return bytes(str(int(bytes(job)) + 2), 'utf')
        return job


parser = argparse.ArgumentParser(description="Clam Client")
parser.add_argument('--id', default=None, type=str)
parser.add_argument('--name', default=None, type=str)
parser.add_argument('--port', default=0, type=int)
ns, unknown = parser.parse_known_args()


if __name__ == '__main__':
    EchoClient(
        port=ns.port,
        backbone_url='http://localhost:5009/',
        id=ns.id,
        name=ns.name,
    ).run()
