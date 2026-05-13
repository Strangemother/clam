import json
import pathlib
import re

from flask import Flask, jsonify, render_template, request

import power_graph.nodes  # noqa: F401 - registers built-in node types as a side effect
from power_graph.node_registry import NodeRegistry

app = Flask(__name__)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
LAYOUTS_DIR = PROJECT_ROOT.parent / 'func-pipes' / 'layouts'


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

    safe_name = re.sub(r'[^\w\s-]', '', name).strip()
    safe_name = re.sub(r'[\s]+', '-', safe_name)
    if not safe_name:
        return jsonify({'error': 'name contains no valid characters'}), 400

    layout = {
        'nodes': data.get('nodes', []),
        'connections': data.get('connections', []),
        'edges': data.get('edges', {}),
    }

    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = LAYOUTS_DIR / f'{safe_name}.json'
    dest.write_text(json.dumps(layout, indent=2))

    return jsonify({'saved': dest.name})