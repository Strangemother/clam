from flask import Flask, render_template
from modelling import *
import wrappers

app = Flask(__name__)


def main():
    app.run(debug=True)


@app.route("/v1/services/")
def get_services():
    """Read and return the service JSON
    """
    return get_data_file('services.json')


@app.route("/v1/services/<name>/api/tags/")
def get_service(name):
    """Read and return the service JSON
    """
    res = get_api_tags(name)
    return res


@app.route("/v1/services/<name>/api/ps/")
def get_ps(name):
    """Read and return the service JSON
    """
    res = get_api_ps(name)
    return res

@app.route("/v1/services/<name>/running/")
def service_model_running(name):
    models = get_api_ps(name)
    return clean_models(models)


@app.route("/v1/services/<name>/models/")
def service_model_list(name):
    """A cleaner list of _models_
    """
    models = get_api_tags(name)
    return clean_models(models)

from flask import request

def get_unit(name):

    obj = get_service_object(name)
    Unit = getattr(wrappers, obj['class_name'])

    host, port = obj['url'].rsplit(':', 1)
    return Unit(host=host, port=port)


@app.route("/v1/services/<name>/")
def service_model_index(name):
    """This endpoint model
    """
    obj = get_service_object(name)

    models = {}

    if obj['type'] == 'jan':
        return get_unit(name).get_model_list()


    if obj['type'] == 'olloma':
        ol = get_unit(name).get_model_list()
        return ol

        running = get_api_ps(name)
        models = get_api_tags(name)
        names = set([x['name'] for x in running['models']])
        for model in models['models']:
            model['running'] = model['name'] in names
    return models


@app.route('/v1/form/prompt/', methods=['POST'])
def post_form_prompt():
    """The minimal tool to perform a prompt to a response endpoint.
    """
    prompt = request.form['prompt']
    name = request.form['name']
    model = request.form.get('model')

    obj = get_service_object(name)
    Unit = getattr(wrappers, obj['class_name'])

    host, port = obj['url'].rsplit(':', 1)
    u = Unit(host=host, port=port)
    print('prompt', u, prompt)
    res = u.prompt(prompt, model=model)
    print(res)
    return res

@app.route("/")
def hello_world():
    return render_template('index.html')


if __name__ == '__main__':
    main()