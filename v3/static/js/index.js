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


const cache = {
    stashValue: ''
    , counter: 0
    , primarySocket: undefined
    , socketConnected: false

}



const foregroundEvent = async function(data, ev) {
    // push to magic presenter.
    if(data['done'] == true){
        // winner
        setTimeout(()=>{
            data.type = data['role']
            data.text =  cache.stashValue
            app.messages.push(data)
            setTimeout(()=>{
                app.$refs.presenter.innerHTML = cache.stashValue = ''
                // app.$refs.status.innerHTML = data.role
                app.partialState.status = 'waiting'
                cache['counter'] = 0
                // app.$refs.counter.innerHTML = cache['counter']
                app.partialState.counter = cache['counter']
            }, 5)
        }, 500)
        return
    }

    cache['stashValue'] += data.content
    cache['counter'] += 1
    // console.log(cache['counter'])
    let n = `<span>${data.content}</span>`
    // console.log('.')
    app.partialState.counter = cache['counter']
    app.partialState.status = data.role

    // app.$refs.counter.innerHTML = cache['counter']
    // app.$refs.status.innerHTML = data.role

    app.$refs.presenter.innerHTML += data.content
    // app.$refs.presenter.innerHTML += n
}


const tokensPerSecond = function(eval_count, eval_duration) {
    return eval_count / eval_duration * 10^9.
}

let recvJSONEvent = async function(ev) {
    // console.log(ev)
    // console.log('.')

    let data = JSON.parse(ev.data)
    let nodeMap = {
        foreground: foregroundEvent//(data, ev)
    }

    let node = data['node']
    let f = nodeMap[node]

    if(f == undefined) {
        if(node == undefined) {
            return
        }
        console.warn('Unknown node type', node)
        app.messages.push({ type: 'message', text: data })
        return
    }
    return await f(data, ev)
}

let getSocket = function() {
    if(cache.primarySocket == undefined) {
        let url = app.$refs.url.value
        cache.primarySocket = connectSocket(url)
    }

    return cache.primarySocket
}

const newSocket = function(){
    cache.primarySocket = undefined;
    return getSocket()
}

let sendTextMessage = async function(t, role='user') {
    app.messages.push({ type: role, text: t })
    let v = JSON.stringify({'text': t, role:role})
    let ws = getSocket()
    ws.send(v)
}


let sendJSONMessage = async function(data) {
    let t = JSON.stringify(data)
    app.messages.push({ type: 'assistant', text: `send ${t.length}` })
    let ws = getSocket()
    ws.send(t)
}


const sendFirstMessage = async function() {
    console.log('Send first message', uuid)
    await sendJSONMessage({uuid})
}


const reactive = PetiteVue.reactive
const createMiniApp = function() {

    let app = {
        cacheCopy: reactive(cache)
        , messages: reactive([])
        , partialState: reactive({
            status: "waiting"
            , counter: 0
        })

        , async enterSubmitText(ev) {
            /* EnterKey _only_ created new line.
               Adding a modifier sends the text.
            */
            let modified = ev.ctrlKey || ev.shiftKey
            if(modified) { // allow key entry
                return true
            }
            this.partialState.status = 'submitting'
            ev.preventDefault()
            console.log('enterSubmitText')
            await sendTextMessage(ev.target.value)
            ev.target.value = ''
        }
        , reconnect(){
            newSocket()
        }
    }

    const res = PetiteVue.createApp(app)
    res.mount('#mini-app')
    return app
};


const app = createMiniApp();
newSocket()
