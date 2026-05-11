import os, json
from flask import Flask, render_template, request, jsonify
from prompting import prompting_bp

LAYOUTS_DIR = os.path.join(os.path.dirname(__file__), 'layouts')

app = Flask(__name__)
app.register_blueprint(prompting_bp)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/logic')
def logic():
    return render_template('logic.html')


@app.route('/plugs')
def plugs():
    return render_template('plugs.html')


@app.route('/power')
def power():
    return render_template('power.html')


@app.route('/inputs')
def inputs():
    return render_template('inputs.html')


@app.route('/power2')
def power2():
    os.makedirs(LAYOUTS_DIR, exist_ok=True)
    files = [f[:-5] for f in os.listdir(LAYOUTS_DIR) if f.endswith('.json')]
    return render_template('power2.html', layout_files=sorted(files))


@app.route('/power2/layouts', methods=['GET'])
def list_layouts():
    os.makedirs(LAYOUTS_DIR, exist_ok=True)
    files = [f[:-5] for f in os.listdir(LAYOUTS_DIR) if f.endswith('.json')]
    return jsonify(sorted(files))


@app.route('/power2/layouts/<name>', methods=['GET'])
def load_layout(name):
    path = os.path.join(LAYOUTS_DIR, name + '.json')
    if not os.path.isfile(path):
        return jsonify({'error': 'not found'}), 404
    with open(path) as f:
        return f.read(), 200, {'Content-Type': 'application/json'}


@app.route('/power2/layouts/<name>', methods=['POST'])
def save_layout(name):
    os.makedirs(LAYOUTS_DIR, exist_ok=True)
    path = os.path.join(LAYOUTS_DIR, name + '.json')
    data = request.get_json(force=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({'ok': True, 'name': name})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
