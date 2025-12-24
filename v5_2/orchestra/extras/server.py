"""
This server module is part of the Orchestra v5.2 package.
It handles server-side operations and functionalities.
"""

"""
    / [GET]                     home
    /register [POST]            register unit
    /unregister/<id> [DELETE]   unregister unit
    /units                      list registered units
    /dispatch [POST]            dispatch task (from client)
    /job_result [POST]          receive job result (from client)
"""

from flask import Flask, request, jsonify
from datetime import datetime, timezone
from flask import render_template, redirect, url_for
import uuid


app = Flask(__name__)

# In-memory register of active units (keyed by ID)
register = {
    # id: data
}



def main(**client_data):
    host = client_data.get('host','127.0.0.1')
    port = client_data.get('port', 5009)
    app.run(host=host, port=port, debug=False, use_reloader=False)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('backbone.html', units=register)


@app.route('/register', methods=['POST'])
def register_unit():
    """Accept unit registration."""
    data = request.get_json()
    unit_id = data.get('id') or str(uuid.uuid4())
    print('Registering', unit_id)
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
    """Return an immediate receipt, and dispatch task to unit."""
    # data = request.get_json()
    yield jsonify({"status": "ok"}), 200


import graph
import requests


@app.route('/job_result', methods=['POST'])
def receive_job_result():
    """Receive job result from a client."""
    data = request.get_data()
    # resolve the receipt ID of this job
    receipt_id = request.headers.get('X-Receipt-ID', 'unknown')
    client_id = request.headers.get('X-Client-ID', 'unknown')
    print('Received job result:', receipt_id, client_id, data)
    # send to graphed clients.
    # Resolve friendly name 
    name = register.get(client_id, {}).get('name', 'unknown')
    print(f"[Backbone] Job result from {name} ({client_id}") 
    
    g = graph.GRAPH
    dests = g.get(name, [])
    for other in dests:
        # find all clients of this type
        other_info = register.get(other)
        if other_info is None:
            continue
        url = other_info.get('url', None)
        if url:
            print(f"[Backbone] Forwarding job result to {other} at {url}")
            requests.post(url, data=data)

    # Acknowledge receipt
    return jsonify({"status": "received"}), 200


if __name__ == '__main__':
    main()