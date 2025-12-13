"""
Simple standalone Python client for receiving and processing messages.
Uses Flask for HTTP communication and threading for non-blocking work.
"""
import os
from flask import Flask, request, jsonify, render_template
from threading import Thread, Timer
import logging
import requests

# Suppress Flask's default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

import socketserver


original_socket_bind = socketserver.TCPServer.server_bind
def socket_bind_wrapper(self):
    ret = original_socket_bind(self)
    print("Socket running at {}:{}".format(*self.socket.getsockname()))
    # Recover original implementation
    socketserver.TCPServer.server_bind = original_socket_bind
    return ret

socketserver.TCPServer.server_bind = socket_bind_wrapper   #Hook the wrapper

import uuid


class Client:

    host = '127.0.0.1'
    port = 9000
    name = None # 'Client'

    def __init__(self, work_function=None,
                host=None, port=None, name=None,
                auto_start=None, on_start=None):
        """
        Initialize the client with a work function.

        Args:
            work_function: Function to call when a message is received.
                          Should accept a message and return a result.
            host: Host to bind to (default: 0.0.0.0)
            port: Port to listen on (default: 8000)
            name: Name of this client (default: 'Client')
            auto_start: Delay in seconds before auto-starting a process (default: None)
            on_start: Function to call when auto-start triggers (default: None)
        """
        self.work_function = work_function or self.perform_work
        self.host = host or self.host
        self.port = port or self.port
        self.name = name or self.name
        self.auto_start = auto_start
        self.on_start = on_start
        self.app = Flask(__name__)
        self._setup_routes()

    def get_name(self):
        if self.name is None:
            return self.__class__.__name__
        return self.name

    def wake(self):
        self.cache = {}

    def add_handler(self, _id, on_get, *a, **kw):
        self.cache[_id] = on_get, (a, kw,)

    def as_safe_cache_path(self, filename):
        p = self.as_cache_path(filename)
        os.makedirs(p.parent, exist_ok=True)
        return p

    def perform_work(self, message):
        return

    def get_form_field_names(self):
        return ['message']

    def process_form(self, form):
        # message = form.get('message', '')
        r = {}
        for k in self.get_form_field_names():
            v = form.get(k)
            r[k] = v
        # return {"message":message}
        return r

    def on_get_own_job(self, resp):
        print('\n\nMy own job response', resp, '\n\n')
        # Store this for the view test
        self.self_work_results[resp['id']] = resp

    def _setup_routes(self):
        """Setup Flask routes for receiving messages."""
        self.self_work_results = {}

        @self.app.route('/result/<key>/', methods=['GET'])
        def last_cache_data(key=None):
            # return the result for the key.
            return self.self_work_results.get(key)

        @self.app.route('/clear/<key>/', methods=['GET'])
        def clear_cache_data(key=None):
            # delete the result for the key.
            return self.self_work_results.pop(key, None)

        @self.app.route('/', methods=['GET', 'POST'])
        def home():
            """Home page with client info and message form."""

            post_result = None
            rid = None
            if request.method == 'POST':
                # message = request.form.get('message', '')
                d = self.process_form(request.form)
                d['sender_url'] = f"http://{self.host}:{self.port}"
                print(f'\n\nPOST from: {d["sender_url"]}\n\n')
                r = on_recv_message(d)
                rid = r['id']
                if rid is not None:
                    print('\nRegistering self handler', rid, '\n\n')
                    self.add_handler(rid, self.on_get_own_job)
                post_result = str(r)
                print(f'Will wait for Receipt: {post_result}\n')

            message = self.get_template('demos/one').render()
            return render_template('home.html',
                            post_result=post_result,
                            receipt_id=rid,
                            client_name=self.get_name(),
                            port=self.port,
                            message=message,
                            form_fields=self.get_form_field_names(),
                            )

        @self.app.route('/message', methods=['POST'])
        def receive_message():
            """Handle incoming messages."""
            data = request.get_json()
            return jsonify(on_recv_message(data)), 202

        def on_recv_message(data):
            message = data.get('message', '')
            _id = data.get('id', uuid.uuid4().hex.upper()[0:10])
            # response_id = _id
            sender_url = data.get('sender_url', None)

            # Print immediate thanks response
            print(f"[{self.get_name()}] Received: {message}")
            print(f"[{self.get_name()}] Response: thanks, will send result to")
            print(f"[{self.get_name()}] sender_url: {sender_url}, id {_id}")

            # Process work in a separate thread for non-blocking behavior
            thread = Thread(target=self._process_async, args=(message, sender_url, _id))
            thread.daemon = True
            thread.start()

            # Immediately return acknowledgment
            return {
                'status': 'received',
                'message': 'thanks',
                'id': _id,
            }

        @self.app.route('/work', methods=['POST'])
        def do_work():
            """Synchronous endpoint that waits for result."""
            data = request.get_json()
            message = data.get('message', '')

            # try:
            result = self.work_function(message)
            return jsonify({
                'status': 'success',
                'result': result
            }), 200
            # except Exception as e:

                # return jsonify({
                #     'status': 'error',
                #     'error': str(e)
                # }), 500

        @self.app.route('/response', methods=['POST'])
        def receive_response():
            """Receive a response from another client."""
            data = request.get_json()
            d = self.receive_response(data)
            return jsonify(d), 200

        @self.app.route('/ping', methods=['GET'])
        def ping():
            """Health check endpoint."""
            return jsonify({'status': 'ok'}), 200

    def receive_response(self, data):
        """/response endpoint from a url
        """
        if self.client_id_route_receive_response(data) is True:
            return {'status': 'ok', 'action': 'routed'}


        message = data.get('message', '')
        print(f'[{self.get_name()}]::receive_response: "{message}"')
        return {'status': 'ok', 'message': message}


    def client_id_route_receive_response(self, data):
        """/response endpoint from a url
        """
        message = data#.get('message', '')
        print(f'[{self.get_name()}]::receive_response: "{message}"')
        _id = message.get('id', None)

        if _id in self.cache:
            print('CACHE HIT', _id)
            f, (a, kw) = self.cache[_id]
            f(*a, message, **kw)
            del self.cache[_id]
            return True
        return False
        # return {'status': 'ok', 'message': message}


    def _process_async(self, message, sender_url=None, response_id=None):
        """Process work asynchronously in a separate thread."""
        # try:
        print(f'_process_async. Will send to {sender_url} with id {response_id}')
        print('running', str(self.work_function))
        result = self.work_function(message)
        print('!  Result -- ', result)
        if result is None:
            print(f'\n\n[ISSUE]: Work function did not return a result: {self.work_function}\n')
        if result:
            # If there's a result and we know who sent the message, send it back to them
            if sender_url:
                print(f'\n\nResult complete for {response_id}. sending to {sender_url}\n')
                self._send_response(sender_url, result, response_id)
            else:
                print(f"[{self.get_name()}] Completed work: {result}")
        # except Exception as e:
        #     print(f"[{self.get_name()}] Error processing work: {e}")

    def send_message(self, target_url, message):
        """Send a message to another client."""
        # try:
        # Include our URL so the receiver can send responses back
        sender_url = f"http://localhost:{self.port}"
        response = requests.post(f"{target_url}/message", json={
            'message': message,
            'sender_url': sender_url
        })
        print(f"[{self.get_name()}] Sent to {target_url}: {message}")
        return response.json()
        # except Exception as e:
        #     print(f"[{self.get_name()}] Error sending message: {e}")
        #     return None

    def _send_response(self, target_url, response_message, response_id=None):
        """Send a response message back to the sender."""
        # try:
        requests.post(f"{target_url}/response", json={
                'message': response_message,
                'id': response_id,
            })
        # except Exception as e:
        #     print(f"[{self.get_name()}] Error sending response: {e}")

    def start(self):
        """Start the client and listen for messages."""
        print(f"[{self.get_name()}] listening on http://{self.host}:{self.port}")

        # Setup auto-start if configured
        if self.auto_start and self.on_start:
            print(f"[{self.get_name()}] Will auto-start in {self.auto_start} seconds...")
            timer = Timer(self.auto_start, self.on_start)
            timer.daemon = True
            timer.start()
        self.wake()
        self.app.run(host=self.host, port=self.port, debug=True)
