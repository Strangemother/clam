"""Client main process with pipe communication."""
from multiprocessing import Process, Pipe


def _run_server(conn, client_data):
    """Run the Flask server in a subprocess."""
    from . import server
    res = server.run(conn, client_data)
    return res


class Client:
    """
    Base client class. Subclass and override `process_job`.

    Example:
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
        # Stuff like register/update/die 
        if data.get('type') == 'register':
            self.given_id = data.get('id', None)
            print(f"[Client] Registered with ID: {self.given_id}")
        pass

    def run(self):
        """Start the client and process jobs forever."""
        # This is anything you want to sent to the server 
        # on registration
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
                    # not a job, just info
                    self.process_category(data)
                    continue

                result = self.process_job(data)
                parent_conn.send({'result': result, '_job_id': job_id})
        except KeyboardInterrupt:
            pass
        finally:
            self._proc.terminate()
            self._proc.join()


if __name__ == '__main__':
    # Example usage
    class EchoClient(Client):
        def process_job(self, job):
            return {'echo': job}

    EchoClient().run()
