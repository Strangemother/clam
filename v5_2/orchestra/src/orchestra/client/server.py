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
        _loop_wait()


def _loop_wait():
    try:
        msg = conn.recv()
    except EOFError:
        return

    job_id = msg.pop('_job_id', None)
    result = msg.get('result', None)

    with pending_lock:
        job_info = pending_jobs.pop(job_id, None)

    if not job_info:
        return

    url = job_info.get('receipt_url') or client_data.get('backbone_url')
    if not url:
        return

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


from urllib.parse import urlparse
import contextlib
import errno
from socket import error as SocketError
from socket import SO_REUSEADDR
from socket import socket
from socket import SOL_SOCKET

LOCALHOST = '127.0.0.1'


def reserve(ip=LOCALHOST, port=0):
    """Bind to an ephemeral port, force it into the TIME_WAIT state, and unbind it.

    This means that further ephemeral port alloctions won't pick this "reserved" port,
    but subprocesses can still bind to it explicitly, given that they use SO_REUSEADDR.
    By default on linux you have a grace period of 60 seconds to reuse this port.
    To check your own particular value:
    $ cat /proc/sys/net/ipv4/tcp_fin_timeout
    60

    By default, the port will be reserved for localhost (aka 127.0.0.1).
    To reserve a port for a different ip, provide the ip as the first argument.
    Note that IP 0.0.0.0 is interpreted as localhost.
    """
    port = int(port)
    with contextlib.closing(socket()) as s:
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            s.bind((ip, port))
        except SocketError as e:
            # socket.error: EADDRINUSE Address already in use
            if e.errno == errno.EADDRINUSE and port != 0:
                s.bind((ip, 0))
            else:
                raise

        # the connect below deadlocks on kernel >= 4.4.0 unless this arg is greater than zero
        s.listen(1)

        sockname = s.getsockname()

        # these three are necessary just to get the port into a TIME_WAIT state
        with contextlib.closing(socket()) as s2:
            s2.connect(sockname)
            sock, _ = s.accept()
            with contextlib.closing(sock):
                return sockname[1]


def _get_reachable_ip(backbone_url=None):
    """
    Get the IP address that can be used to reach this machine.

    If backbone_url is provided, determines which local IP can reach that host.
    Otherwise, falls back to the default route IP or localhost.
    """
    # Try to determine which interface would be used to reach the backbone
    if backbone_url:
        try:
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

    if port == 0:
        port = data['served_port']

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


from werkzeug.serving import make_server

def run(pipe_conn, data):
    """Run the Flask server with pipe connection."""
    host = data.get('host', LOCALHOST)
    port = data.get('port', 5001)
    # if port == 0:
    #     port = reserve(host)
    print('Reserving Port:', port)
    server = make_server(host, port, app)
    resolved_port = server.server_port

    data['served_port'] = resolved_port

    print(f"Serving on {host}:{resolved_port}")
    # send info to the backbone
    server_info = _register_client(data) or {}
    server_info['served_port'] = data['served_port']
    data['id'] = server_info.get('id')
    set_connection(pipe_conn, data)

    pipe_conn.send({
        **server_info,
        'category': 'info',
        'type': 'register',
    })


    server.serve_forever()

    # app.run(host=host, port=port, debug=False, use_reloader=False)
