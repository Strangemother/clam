"""Backbone server for orchestrating clients.

Endpoints:
    / [GET]                     home
    /register [POST]            register unit
    /register/<id> [DELETE]     unregister unit
    /units [GET]                list registered units
    /dispatch [POST]            dispatch task
    /job_result [POST]          receive job result
"""
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# In-memory register of active units (keyed by ID)
register = {}

from .graph import graph_get


def main(host='127.0.0.1', port=5009):
    """Run the backbone server."""
    app.run(host=host, port=port, debug=False, use_reloader=False)


@app.route('/', methods=['GET'])
def index():
    """Home endpoint."""
    return jsonify(status='ok', units=len(register))


@app.route('/register', methods=['POST'])
def register_unit():
    """Accept unit registration."""
    data = request.get_json()
    unit_id = data.get('id') or str(uuid.uuid4())
    data['id'] = unit_id
    data['registered_at'] = datetime.now(timezone.utc).isoformat()
    register[unit_id] = data

    name = data.get('name') or unit_id
    register[name] = data

    return jsonify({
        "status": "registered",
        "id": unit_id,
        "name": name,
        "total": len(register)
    }), 200


@app.route('/register/<unit_id>', methods=['DELETE'])
def unregister_unit(unit_id):
    """Remove a unit from the register."""
    if unit_id in register:
        del register[unit_id]
        return jsonify({"status": "unregistered", "id": unit_id}), 200
    return jsonify({"status": "not_found", "id": unit_id}), 404


@app.route('/units', methods=['GET'])
def list_units():
    """List all registered units."""
    return jsonify({"units": register, "count": len(register)}), 200


@app.route('/dispatch', methods=['POST'])
def dispatch_task():
    """Dispatch task to a unit."""
    return jsonify({"status": "ok"}), 200


@app.route('/job_result', methods=['POST'])
def receive_job_result():
    """Receive job result from a client."""
    data = request.get_data()
    receipt_id = request.headers.get('X-Receipt-ID', 'unknown')
    client_id = request.headers.get('X-Client-ID', 'unknown')

    # Resolve friendly name
    name = register.get(client_id, {}).get('name', 'unknown')

    # Forward to graphed clients
    dests = graph_get(name, [])
    for other in dests:
        other_info = register.get(other)
        if other_info is None:
            continue
        url = other_info.get('url')
        if url:
            try:
                requests.post(url, data=data, timeout=10)
            except requests.RequestException:
                pass

    return jsonify({"status": "received"}), 200


def set_graph(g):
    """Set the routing graph."""
    global graph
    graph = g
