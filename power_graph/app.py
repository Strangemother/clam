import sys
import json
import re
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent / 'src'))

import power_graph.nodes  # noqa — side-effect: registers all built-in node types
from power_graph.node_registry import NodeRegistry

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

LAYOUTS_DIR = pathlib.Path(__file__).parent.parent / 'func-pipes' / 'layouts'


@app.route('/')
def index():
    return render_template('index.html', catalog=NodeRegistry.catalog_by_group())


@app.route('/api/layout/save', methods=['POST'])
def save_layout():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'invalid JSON body'}), 400

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400

    # Sanitize: allow alphanumeric, hyphens, underscores, spaces → replace spaces with hyphens
    safe_name = re.sub(r'[^\w\s-]', '', name).strip()
    safe_name = re.sub(r'[\s]+', '-', safe_name)
    if not safe_name:
        return jsonify({'error': 'name contains no valid characters'}), 400

    nodes       = data.get('nodes', [])
    connections = data.get('connections', [])
    edges       = data.get('edges', {})

    layout = {'nodes': nodes, 'connections': connections, 'edges': edges}

    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = LAYOUTS_DIR / f'{safe_name}.json'
    dest.write_text(json.dumps(layout, indent=2))

    return jsonify({'saved': str(dest.name)})


if __name__ == '__main__':
    app.run(debug=True, port=5002, host='0.0.0.0')
