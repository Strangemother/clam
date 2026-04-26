/*

Connect to the backend, start receiving socket info.
 */

// const url = 'ws://localhost:8765'
const uuid = Math.random().toString(32).slice(2)


let connectSocket = function(endpoint) {
    console.log('new socket')
    let ws = new WebSocket(endpoint)

    ws.onmessage = async function(ev){
        await recvJSONEvent(ev)
    }

    ws.onopen = async function(ev){
        console.log("open", ev)
        app.messages.push({ type: 'socket', text: 'connected' })
        app.cacheCopy.socketConnected = true
        await sendFirstMessage()
    }


    ws.onerror = function(ev){
        app.messages.push({ type: 'socket', text: 'error' })
        console.error(ev)
    }


    ws.onclose = function(ev){
        app.messages.push({ type: 'socket', text: 'closed' })
        console.log("closed", ev)
        app.cacheCopy.socketConnected = false;
    }

    return ws
}

const runIndexApp = function() {

    // from pipes-ui-app.js
    const app = createUIApp('#mini_app');
    window.app = app;

    // from pipes-winbox-app.js
    runPipes({
        backLayerSelector: '.canvas-container.back canvas'
        , foreLayerSelector: '.canvas-container.fore canvas'
        , dragspaceSelector: 'main'
    })

    // from graph-demo.js
    bootDemoGraph()
}


;runIndexApp();