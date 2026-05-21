import os, json
from flask import Flask, render_template, request, jsonify




"""
In the v2, we should be able to write plain exposure on the graph

input args can become inbound pips
results are send _back_ through the pipe
    or sent to a default pip (default 0)
"""


def my_node_plain(in_value):
    res = {}
    return res # default send to out pip
    # alt: send _back_.


def node_passthrough(in_value):
    return in_value


def node_multiply(in_value, multiplier=2):
    """The second input pip has a default.
    My preference for a node like this, is the alt-inbound pip should always
    recieve the _current_ pip connected value.

    The value is either default - or from a connected node.
    This means this function needs wrapper storage, ensuring the connected
    node value is cached or accessible.

        node = Node(node_multiply)
        node.pips_inbound()
        [in_value, multiplier]

    Therefore when:

        mult_node -> 4 -> (multiplier pip) -> node

    the value `4` is stored for recall

        node(v)
            in_value=v, multiplier=4
    """
    return in_value * multiplier


class Node:
    """graph living class, for easier access to the function and its pips.
    """

    def __init__(self, func, **data):
        self.__dict__.update(data)
        self.func = func
        self.name = self.func.__name__


    def get_pips_inbound(self):
        # get from func vars
        return ['in']

    def get_pips_outbound(self):
        return ['out']



def my_node_pip_call(pip_a:str, pip_b: str):
    """A non-async node would typically wait. but an event is stacked for later.

    """
    res = {}
    out_pip = graph.get_outbound('my_node_pip_call') # default to first
    out_pip.emit("some result") # Is an event.

    return res # default send to out pip
    # alt: send _back_.


class Pip:

    def emit(self, data):
        self.pseudo_emit(self.name, data)

    def pseudo_emit(self, name, data):
        event = {
            name: name,
            data: data,
        }

        graph.events.append(event)




app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


nodes = [
        Node(node_passthrough),
        Node(node_multiply),
    ]

@app.route('/nodes/')
def nodes_list():
    return [x.name for x in nodes]


if __name__ == '__main__':
    app.run(debug=True, port=5002, host='0.0.0.0')
