"""Flask server process for receiving messages.

Runs in a subprocess, manages receipts and job tracking.

- Receives jobs via HTTP endpoints
- Sends jobs to main process via pipe
- Listens for results from main process
- Sends results to receipt URLs
"""
import socket
import threading
import uuid
from datetime import datetime

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
conn = None
client_data = {}
pending_jobs = {}
pending_lock = threading.Lock()


def set_connection(pipe_conn, data):
    """Set the pipe connection for communication with main process."""
    global conn, client_data
    conn = pipe_conn
    client_data = data
    thread = threading.Thread(target=_result_listener, daemon=True)
    thread.start()


def _result_listener():
    """Background thread that listens for results and sends to receipt URL."""
    while True:
        try:
            msg = conn.recv()
            job_id = msg.pop('_job_id', None)
            result = msg.get('result', None)

            with pending_lock:
                job_info = pending_jobs.pop(job_id, None)

            if not job_info:
                continue

            url = job_info.get('receipt_url') or client_data.get('backbone_url')
            if not url:
                continue

            url = url.rstrip('/')
            url = f"{url}/job_result"

            headers = {
                'X-Receipt-ID': job_id,
                'X-Client-ID': client_data.get('id', '0'),
            }

            try:
                requests.post(url, data=result, timeout=10, headers=headers)
            except requests.RequestException:
                pass
        except EOFError:
            break


@app.route('/')
def home():
    """Home endpoint."""
    return jsonify(status='ok')


@app.route('/jobs')
def jobs():
    """List pending jobs."""
    with pending_lock:
        return jsonify(jobs=list(pending_jobs.keys()))


@app.route('/receive', methods=['POST'])
@app.route('/job', methods=['POST'])
def receive():
    """Receive job, queue it for processing."""
    data = request.data
    receipt_url = request.headers.get('X-Receipt-URL')
    job_id = request.headers.get('X-Job-ID', str(uuid.uuid4()))

    if conn is None:
        return jsonify(error='No connection'), 500

    with pending_lock:
        pending_jobs[job_id] = {
            'receipt_url': receipt_url,
            'id': job_id,
            'datetime': datetime.now().isoformat(),
        }

    conn.send({'_job_id': job_id, 'data': data})
    return jsonify(ok=True, count=len(pending_jobs), job_id=job_id)


def _get_reachable_ip(backbone_url=None):
    """
    Get the IP address that can be used to reach this machine.
    
    If backbone_url is provided, determines which local IP can reach that host.
    Otherwise, falls back to the default route IP or localhost.
    """
    # Try to determine which interface would be used to reach the backbone
    if backbone_url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(backbone_url)
            backbone_host = parsed.hostname or 'localhost'
            backbone_port = parsed.port or 80
            
            # Create a socket and connect to backbone to see which local IP is used
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # UDP connect doesn't actually send packets, just determines route
                s.connect((backbone_host, backbone_port))
                return s.getsockname()[0]
        except Exception:
            pass
    
    # Fallback: get default route IP
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception:
        pass
    
    # Last resort
    return '127.0.0.1'


def _register_client(data):
    """Register the client with the backbone server."""
    host = data.get('host', '127.0.0.1')
    port = data.get('port', 5001)
    backbone_url = data.get('backbone_url')
    
    # If host is 0.0.0.0 (listen on all), find the actual reachable IP
    if host in ('0.0.0.0', ''):
        host = _get_reachable_ip(backbone_url)
    
    data.setdefault('url', f'http://{host}:{port}/receive')

    backbone_url = data.get('backbone_url')
    if not backbone_url:
        return None

    url = backbone_url.rstrip('/')
    try:
        res = requests.post(f'{url}/register', json=data, timeout=3)
        return res.json()
    except requests.RequestException:
        return {}


def run(pipe_conn, data):
    """Run the Flask server with pipe connection."""
    host = data.get('host', '127.0.0.1')
    port = data.get('port', 5001)

    server_info = _register_client(data) or {}
    data['id'] = server_info.get('id')

    set_connection(pipe_conn, data)

    pipe_conn.send({
        **server_info,
        'category': 'info',
        'type': 'register',
    })

    app.run(host=host, port=port, debug=False, use_reloader=False)
