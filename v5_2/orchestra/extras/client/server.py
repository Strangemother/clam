"""Flask server process for receiving messages.

- Runs in a background process.
- manages reciepts and job tracking.

---

- has endpoints to receive jobs
- sends jobs to main process (the client)
- listens for results from main process results
- sends results to receipt URLs

---

To use this, use the Client class in client.py.

    class EchoClient(Client):
        def process_job(self, job):
            return {'echo': job}

    EchoClient().run()
"""
import threading
import uuid

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
conn = None
pending_jobs = {}  # Shared dict: job_id -> {'receipt_url': ..., ...}
pending_lock = threading.Lock()


def set_connection(pipe_conn, client_data):
    """Set the pipe connection for communication with main process."""
    global conn
    conn = pipe_conn
    # Start background thread to handle results
    thread = threading.Thread(target=_result_listener, 
                            daemon=True, 
                            args=(client_data,)
                        )
    thread.start()


def _result_listener(client_data):
    """Background thread that listens for results and sends to receipt URL.
    
    parent_conn.send({'result': result, '_job_id': job_id})
    
    """
    while True:
        try:
            msg = conn.recv()
            job_id = msg.pop('_job_id', None)
            result = msg.get('result', None)
            print(f"[client_server] Got result for job {job_id}: {result}")
            # Look up and remove the job from pending
            with pending_lock:
                job_info = pending_jobs.pop(job_id, None)

            if job_info:
                url = job_info.get('receipt_url')
                if url is None:
                    # send to the backbone if no receipt url
                    url = client_data.get('backbone_url')
                
                if url.endswith('/'):
                    url = url[:-1]
                url = f"{url}/job_result"
                if url:
                    try:
                        # add receipt id header
                        headers = {
                            'X-Receipt-ID': job_id,
                            'X-Client-ID': client_data.get('id','0'),
                        }
        
                        print(f"[client_server] Sending result to {url} with headers {headers}")   

                        requests.post(url, 
                                    data=result, 
                                    timeout=10, 
                                    headers=headers
                                )
                    except requests.RequestException:
                        pass  # Log or handle failed delivery
                else:
                    print(f"[client_server] No receipt URL for job {job_id}")
        except EOFError:
            break


@app.route('/')
def home():
    """Home endpoint."""
    return jsonify(status='ok')


@app.route('/orchestra')
def orchestra():
    """example backbone endpoint."""
    return jsonify(status='ok')


@app.route('/jobs')
def jobs():
    """List pending jobs."""
    with pending_lock:
        return jsonify(jobs=list(pending_jobs.keys()))

from datetime import datetime

@app.route('/receive', methods=['POST'])
@app.route('/job', methods=['POST'])
def receive():
    """Receive job (likely from the server), queue it for processing."""
    data = request.data
    receipt_url = request.headers.get('X-Receipt-URL')
    job_id = request.headers.get('X-Job-ID', str(uuid.uuid4()))

    if conn is None:
        return jsonify(error='No connection'), 500
    
    # Register the job
    job = register_job(job_id, receipt_url, data)
    # Send job to main process
    conn.send(job)
    # Acknowledge receipt
    return jsonify(ok=True, count=len(pending_jobs), job_id=job_id)


def register_job(job_id, receipt_url, data):
    # Register the job
    with pending_lock:
        job_info =  {
            'receipt_url': receipt_url,
            'id': job_id,
            'datetime': datetime.now().isoformat(),
        }
        pending_jobs[job_id] = job_info
    # return job like dict for the main process
    return {
        '_job_id': job_id,
        'data': data,
    }


def register_client(client_data):
    """Register the client with the server."""
    host = client_data.get('host','127.0.0.1')
    port = client_data.get('port',5001)
    print(f"[client_server] Registering client at {host}:{port}")
    # if client has backbone url, post to it
    client_data.setdefault('url',f'http://{host}:{port}/receive')
    backbone_url = client_data.get('backbone_url', None) or None 
    if backbone_url is None:
        print("[client_server] No backbone URL provided, skipping registration.")
        return None
    try:
        url = backbone_url
        if url.endswith('/'):
            url = url[:-1]
        res = requests.post(f'{url}/register', 
                        json=client_data, 
                        timeout=3)
    except requests.RequestException as e:
        # requests.exceptions.ConnectionError:
        print(f"[client_server] Failed to register client: {e}")
        return {}
    return res.json()


def run(pipe_conn, client_data):
    """Run the Flask server with pipe connection."""
    host = client_data.get('host','127.0.0.1')
    port = client_data.get('port', 5001)
    server_response_info = register_client(client_data)
    if server_response_info is None:
        server_response_info = {}
    print('[client_server] Registered with server:', server_response_info)
    client_data['id'] = server_response_info.get('id', None)
    set_connection(pipe_conn, client_data)
    pipe_conn.send({
        **server_response_info,
        'category': 'info',
        'type': 'register',
    })
    app.run(host=host, port=port, debug=True, use_reloader=False)

