"""Client main process with pipe communication."""
from multiprocessing import Process, Pipe


def _run_server(conn, client_data):
    """Run the Flask server in a subprocess."""
    from orchestra.client import server
    return server.run(conn, client_data)


class Client:
    """
    Base client class. Subclass and override `process_job`.

    Example:
        from orchestra.client import Client

        class MyClient(Client):
            def process_job(self, job):
                return {'result': job['value'] * 2}

        MyClient().run()
    """

    def __init__(self, host='0.0.0.0', port=5001, **kwargs):
        self.host = host
        self.port = port
        self._conn = None
        self._proc = None
        self.kwargs = kwargs
        self.given_id = kwargs.get('id', None)

    def process_job(self, job):
        """Override this method to handle jobs."""
        raise NotImplementedError("Subclass must implement process_job")

    def process_category(self, data):
        """Handle non-job messages based on category."""
        print(f"[Client] Info: {data}")
        if data.get('type') == 'register':
            self.given_id = data.get('id', None)
            print(f"[Client] Registered with ID: {self.given_id}")

    def run(self):
        """Start the client and process jobs forever."""
        client_data = {
            'host': self.host,
            'port': self.port,
            'name': self.__class__.__name__,
            'id': self.given_id,
            **self.kwargs,
        }

        parent_conn, child_conn = Pipe()
        self._conn = parent_conn
        self._proc = Process(
            target=_run_server,
            args=(child_conn, client_data),
        )
        self._proc.start()

        try:
            while True:
                job = parent_conn.recv()
                job_id = job.get('_job_id')
                data = job.get('data', job)

                if job.get('category') == 'info':
                    self.process_category(data)
                    continue

                result = self.process_job(data)
                parent_conn.send({'result': result, '_job_id': job_id})
        except KeyboardInterrupt:
            pass
        finally:
            self._proc.terminate()
            self._proc.join()
