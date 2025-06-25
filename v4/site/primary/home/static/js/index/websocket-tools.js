/*

Generic hooked functions to help with socket messaging.

 */
class GlobalSocketEvent extends EventBase {}

class RequestSocketConnectEvent extends GlobalSocketEvent {}


let getSocket = function(url) {
    if(url == undefined){
        url = cache.globalSocketEndpoint
    }

    if(cache.primarySocket == undefined) {
        console.log('new socket required.')
        cache.primarySocket = connectSocket(url)
    }
    // cache.used = true
    return cache.primarySocket
}


const sendFirstMessage = async function(addition={}) {
    /* Called by the onopen before the global message is dispatched.
    Here we can define the _Authy_ and assignment steps.
    The next response should be a wake. */
    console.log('Send first message', uuid)
    let data = {
            uuid /* Send a unique string for this session/connection.*/
            // Define what _this_ is. I think colons are cool.
            , role: "user::primary"
            /* Things this interface can do. Such as play audio*/
            , abilities: ['text']
        }

    await sendJSONMessage(Object.assign(data, addition))
}


let sendJSONMessage = async function(data) {
    /* Send a dictionary as a JSON message, first converting the given object
        to a JSON String,
        then collecting the global socket to send the text.

            sendJSONMessage({text: 'window'})

    */
    let t = JSON.stringify(data)
    // app.messages.push({ type: 'assistant', text: `send ${t.length}` })
    let ws = getSocket()
    ws.send(t)
}


let recvJSONEvent = async function(ev) {
    /*
        Called by the websocket onMessage event.
    */
    // console.log('.')
    let data = JSON.parse(ev.data)
    // console.log('message', data, ev)
    GlobalSocketEvent.emit({ type: 'message', data })
    return data
}


let connectSocket = function(endpoint) {
    /* Connect Open a prepared socket, connected to the global event receivers */
    console.log('Connecting to', endpoint)
    let ws = new WebSocket(endpoint)

    ws.onmessage = async function(ev){
        await recvJSONEvent(ev)
    }

    ws.onopen = async function(ev){
        let socket = ev.currentTarget
        console.log("Connected", socket)
        cache.socketConnected = true
        await sendFirstMessage({})
        GlobalSocketEvent.emit({ type: 'open'})
    }

    ws.onerror = function(ev){
        console.error(ev)
        // cache.socketConnected = false
        GlobalSocketEvent.emit({ type: 'error', text: 'error' })
    }

    ws.onclose = function(ev){
        cache.socketConnected = false
        GlobalSocketEvent.emit({ type: 'close', text: 'closed' })
    }

    return ws
}
