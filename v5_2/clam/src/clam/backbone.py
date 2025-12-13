"""Minimal backbone service to track active units."""
from flask import Flask, request, jsonify
import uuid
import requests
from datetime import datetime, timezone
from . import config

app = Flask(__name__)

# In-memory register of active units (keyed by ID)
register = {}


@app.route('/register', methods=['POST'])
def register_unit():
    """Accept unit registration."""
    data = request.get_json()
    unit_id = data.get('id') or str(uuid.uuid4())
    data['registered_at'] = datetime.now(timezone.utc).isoformat()
    register[unit_id] = data
    return jsonify({"status": "registered", "id": unit_id, "total": len(register)}), 200


@app.route('/units', methods=['GET'])
def list_units():
    """List all registered units."""
    return jsonify({"units": register, "count": len(register)}), 200


@app.route('/register/<unit_id>', methods=['DELETE'])
def unregister_unit(unit_id):
    """Remove a unit from the register."""
    if unit_id in register:
        del register[unit_id]
        return jsonify({"status": "unregistered", "id": unit_id}), 200
    return jsonify({"status": "not_found", "id": unit_id}), 404


@app.route('/', methods=['GET', 'POST'])
def index():
    """Manual registration form."""
    from flask import render_template, redirect, url_for
    import json as json_lib

    if request.method == 'POST':
        try:
            data = json_lib.loads(request.form['json_data'])
            unit_id = data.get('id') or str(uuid.uuid4())
            register[unit_id] = data
            return redirect(url_for('index'))
        except json_lib.JSONDecodeError as e:
            return render_template('backbone.html', error=str(e), units=register)

    return render_template('backbone.html', units=register)


def mount(registration=None):
    """Register a unit with the backbone service."""
    import socket

    hostname = socket.gethostname()
    d = {
        "name": hostname,
        # "url": f"http://{hostname}:5000"
    }

    if registration:
        d.update(registration)
    try:
        resp = requests.post("http://localhost:5000/register", json=d, timeout=2)
        data = resp.json()
        unit_id = data.get('id')
        print(f'Backbone registered with ID: {unit_id}')
        return unit_id
    except requests.exceptions.ConnectionError as e:
        print(f'Backbone registration failed: {e}')
        return None


def unmount(unit_id):
    """Unregister a unit from the backbone service."""
    try:
        resp = requests.delete(f"http://localhost:5000/register/{unit_id}", timeout=2)
        data = resp.json()
        print(f'Backbone unregistered: {data}')
        return data
    except requests.exceptions.ConnectionError as e:
        print(f'Backbone unregistration failed: {e}')
        return None


def configure_parser(parser, subparsers):
    """Configure the subparser for backbone service."""

    if subparsers:
        parser = subparsers.add_parser('backbone', help='Run the backbone service')
    parser.set_defaults(func=main)
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser


def main(args=None):
    """Run the backbone service."""
    import argparse

    if args is None:
        parser = argparse.ArgumentParser(description="Backbone service")
        configure_parser(parser)
        args = parser.parse_args()

    # CLI args override config
    host = getattr(args, 'host', None) or config.BACKBONE_HOST
    port = getattr(args, 'port', None) or config.BACKBONE_PORT
    debug = getattr(args, 'debug', False) or config.DEBUG

    print(f'Starting backbone service on {host}:{port}')
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
