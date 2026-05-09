from flask import Flask, render_template
from prompting import prompting_bp

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


if __name__ == '__main__':
    app.run(debug=True, port=5001)
