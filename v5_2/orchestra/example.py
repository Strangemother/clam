"""Example client that echoes jobs back."""
from client.client import Client
import time


class EchoClient(Client):
    def process_job(self, job):
        print(f"[EchoClient] Got job: {job}")
        time.sleep(2)
        return bytes("I like butterscotch.", 'utf-8')
        # return str({'echo': job})


if __name__ == '__main__':
    EchoClient(
        port=5001,
        backbone_url='http://localhost:5009/',
    ).run()
