

REGISTER = {

}


def set_register(uuid, websocket):
    REGISTER[uuid] = websocket


def drop_register(uuid):
    del REGISTER[uuid]


def get_register(uuid):
    return REGISTER[uuid]
