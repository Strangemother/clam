"""
Simple standalone Python client for receiving and processing messages.
Uses Flask for HTTP communication and threading for non-blocking work.
"""

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


class Client:

    host = '127.0.0.1'
    port = 9000
    name = 'Client'

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

    def perform_work(self, message):
        return

    def _setup_routes(self):
        """Setup Flask routes for receiving messages."""

        @self.app.route('/', methods=['GET', 'POST'])
        def home():
            """Home page with client info and message form."""
            if request.method == 'POST':
                message = request.form.get('message', '')
                return str(on_recv_message({"message":message}))
            return render_template('home.html', client_name=self.name, port=self.port)

        @self.app.route('/message', methods=['POST'])
        def receive_message():
            """Handle incoming messages."""
            data = request.get_json()
            return jsonify(on_recv_message(data)), 202

        def on_recv_message(data):
            message = data.get('message', '')
            sender_url = data.get('sender_url', None)

            # Print immediate thanks response
            print(f"[{self.name}] Received: {message}")
            print(f"[{self.name}] Response: thanks")

            # Process work in a separate thread for non-blocking behavior
            thread = Thread(target=self._process_async, args=(message, sender_url))
            thread.daemon = True
            thread.start()

            # Immediately return acknowledgment
            return {
                'status': 'received',
                'message': 'thanks'
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
            message = data.get('message', '')
            print(f"[{self.name}] Got response: {message}")
            return jsonify({'status': 'ok'}), 200

        @self.app.route('/ping', methods=['GET'])
        def ping():
            """Health check endpoint."""
            return jsonify({'status': 'ok'}), 200

    def _process_async(self, message, sender_url=None):
        """Process work asynchronously in a separate thread."""
        # try:
        result = self.work_function(message)
        if result:
            # If there's a result and we know who sent the message, send it back to them
            if sender_url:
                self._send_response(sender_url, result)
            else:
                print(f"[{self.name}] Completed work: {result}")
        # except Exception as e:
        #     print(f"[{self.name}] Error processing work: {e}")

    def send_message(self, target_url, message):
        """Send a message to another client."""
        # try:
        # Include our URL so the receiver can send responses back
        sender_url = f"http://localhost:{self.port}"
        response = requests.post(f"{target_url}/message", json={
            'message': message,
            'sender_url': sender_url
        })
        print(f"[{self.name}] Sent to {target_url}: {message}")
        return response.json()
        # except Exception as e:
        #     print(f"[{self.name}] Error sending message: {e}")
        #     return None

    def _send_response(self, target_url, response_message):
        """Send a response message back to the sender."""
        # try:
        requests.post(f"{target_url}/response", json={'message': response_message})
        # except Exception as e:
        #     print(f"[{self.name}] Error sending response: {e}")

    def start(self):
        """Start the client and listen for messages."""
        print(f"[{self.name}] listening on http://{self.host}:{self.port}")

        # Setup auto-start if configured
        if self.auto_start and self.on_start:
            print(f"[{self.name}] Will auto-start in {self.auto_start} seconds...")
            timer = Timer(self.auto_start, self.on_start)
            timer.daemon = True
            timer.start()

        self.app.run(host=self.host, port=self.port, debug=True)
