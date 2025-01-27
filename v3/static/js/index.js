/*

Connect to the backend, start receiving socket info.
 */

const url = 'ws://localhost:8765'
const uuid = Math.random().toString(32).slice(2)

let ws = new WebSocket(url)


ws.onmessage = async function(ev){
    await recvJSONEvent(ev)
}


ws.onopen = async function(ev){
    console.log("open", ev)
    app.messages.push({ type: 'socket', text: 'connected' })
    await sendFirstMessage()
}


ws.onerror = function(ev){
    app.messages.push({ type: 'socket', text: 'error' })
    console.error(ev)
}


ws.onclose = function(ev){
    app.messages.push({ type: 'socket', text: 'closed' })
    console.log("closed", ev)
}

const cache = {
    stashValue: ''
    , counter: 0
}

const foregroundEvent = async function(data, ev) {
    // push to magic presenter.
    if(data['done'] == true){
        // winner
        setTimeout(()=>{
            app.messages.push({ type: 'message', text: cache.stashValue })
            setTimeout(()=>{
                app.$refs.presenter.innerHTML = cache.stashValue = ''
                app.$refs.status.innerHTML = data.role
                cache['counter'] = 0
                app.$refs.counter.innerHTML = cache['counter']
            }, 5)
        }, 500)
        return
    }

    cache['stashValue'] += data.content
    cache['counter'] += 1
    // console.log(cache['counter'])
    let n = `<span>${data.content}</span>`
    // app.partialState.counter = cache['counter']
    // app.partialState.status = 'receiving'

    app.$refs.counter.innerHTML = cache['counter']
    app.$refs.status.innerHTML = data.role
    app.$refs.presenter.innerHTML += n
}


let recvJSONEvent = async function(ev) {
    // console.log(ev)
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


let sendTextMessage = async function(t) {
    app.messages.push({ type: 'socket', text: `send ${t.length}` })
    let v = JSON.stringify({'text': t})
    ws.send(v)
}


let sendJSONMessage = async function(data) {
    let t = JSON.stringify(data)
    app.messages.push({ type: 'socket', text: `send ${t.length}` })
    ws.send(t)
}


const sendFirstMessage = async function() {
    console.log('Send first message', uuid)
    await sendJSONMessage({uuid})
}


const reactive = PetiteVue.reactive
const createMiniApp = function() {

    let app = {
        messages: reactive([])
        , partialState: reactive({
            status: "waiting"
            , counter: 0
        })
        , async enterSubmitText(ev) {
            /* EnterKey _only_ created new line.
            Adding a modifier sends the text.
            */
            let modified = ev.ctrlKey || ev.shiftKey
            if(modified) {
                // allow key entry
                return true
            }
            this.partialState.status = 'submitting'
            ev.preventDefault()
            console.log('enterSubmitText')
            await sendTextMessage(ev.target.value)
        }
    }

    const res = PetiteVue.createApp(app)
    res.mount('#mini-app')
    return app
};


const app = createMiniApp();
