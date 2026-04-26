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


const cache = {}


const reactive = PetiteVue.reactive

const keyMap = {
    /*
        Apple connects to orange and banana from node one
        apple connects to cherry on node two
     */
    'apple': {
    }
}

const createWindowApp = function(windowApp) {

    let WindowAppConf = {
        textStatus: 'No Status'
        , label: windowApp.title
        , pipsInbound: []
        , pipsOutbound: []

        , addInboundPip(){
            let pip = {
                index:this.pipsInbound.length
            }
            this.pipsInbound.push(pip)
            this.textStatus = `New inbound pip: ${pip.index}`
        }

        , addOutboundPip(){
            let pip = { index:this.pipsOutbound.length }
            this.pipsOutbound.push(pip)
            this.textStatus = `New outbound pip: ${pip.index}`
        }

        , getTip(direction, index=0) {
            let items = direction == 'outbound'? this.pipsOutbound: this.pipsInbound
            if(items == undefined) {
                console.error('No tips', this)
                return
            }

            let res = items[index]
            if(res == undefined) {
                console.error(`No Index ${index}`)
                return
            }

            // add view node
            let nodeId = `${this.label}-${direction}-${index}`
            res['node'] = document.getElementById(nodeId)
            return res
        }

        , pipStartDrag(event, direction="outbound", pipIndex) {
            console.log(`pipStartDrag(${direction}, ${pipIndex})`)
            event.target.classList.add("dragging");
            // Clear the drag data cache (for all formats/types)
            event.dataTransfer.clearData();
            // Set the drag's format and data.
            // Use the event target's id for the data
            let d = {
                label: this.label
                , direction
                , pipIndex
            }

            let content = JSON.stringify(d)
            event.dataTransfer.setData("text/plain", content);
        }

        , pipEndDrag(event, direction="outbound", pipIndex) {
            console.log(`pipEndDrag(${direction}, ${pipIndex})`)
            event.target.classList.remove("dragging");
        }

        , pipOverDrag(event, direction="outbound", pipIndex) {
            // Get the data, which is the id of the source element
            const data = event.dataTransfer.getData("text");
            console.log(`pipOverDrag(${direction}, ${pipIndex}) == ${data}`)
            event.preventDefault()
            // event.target.classList.remove("dragging");
        }

        , pipDrop(event, direction, pipIndex) {
            const content = event.dataTransfer.getData("text");

            const sender = JSON.parse(content)
            const self = {
                label: this.label
                , direction
                , pipIndex
            }

            this.connect(sender, self)

        }

        , connect(sender, receiver) {
            // console.log('Connect from', sender, 'to: ', receiver)
            document.dispatchEvent(new CustomEvent('connectnodes', {
                    detail: {
                        sender
                        , receiver
                    }
                })
            )
        }

    }

    const WindowApp = PetiteVue.createApp(WindowAppConf)
    const _app = WindowApp.mount(windowApp.body)

    // Create default pips 0, 0.
    WindowAppConf.addInboundPip()
    WindowAppConf.addOutboundPip()

    windowApp.vueApp = WindowAppConf
};


const createMiniApp = function() {

    let app = {
        // cacheCopy: reactive(cache)
        // , messages: reactive([])
        // , partialState: reactive({
        //     status: "waiting"
        //     , counter: 0
        // })
        newPanelName: "Strange Apple"
        , windowMap: {}
        , spawnWindow(conf=this.newPanelName) {
            let name = conf.name;
            let winapp = {
                class: [
                    // "no-min"
                    // , "no-max"
                    , "no-full"
                    // , "no-resize"
                    // , "no-move"
                    ]
                , x: "center"
                , y: "center"
                , width: "20%"
                , height: "20%"
                , mount: document
                            .getElementById("window_content")
                            .cloneNode(true)
                , root: document.querySelector("main")

                ,  onclose: function(force){
                    console.log('Unmount app')
                    this.vueApp.unmount()
                    return force;
                    // return !confirm("Close window?");
                },

            };
            Object.assign(winapp, conf);
            let _window = new WinBox(name, winapp);
            createWindowApp(_window)
            this.windowMap[name] = _window
            return _window
        }

        , getTip(label, direction, index=0) {
            let windowApp = this.windowMap[label]
            let unit = windowApp.vueApp.getTip(direction, index)
            return unit
        }
    }

    const res = PetiteVue.createApp(app)

    res.mount('#mini_app')

    app.spawnWindow({name: 'apples', x: '20%'})
    app.spawnWindow({name:'cherry', x: '60%'})

    setTimeout(autoConnectNodes, 300)
    return app
};



const autoConnectNodes = function() {

    /*
    Connect nodes without doing it by hand
     */
    let inverted = {
        "sender": {
            "label": "apples",
            "direction": "inbound",
            "pipIndex": 0
        },
        "receiver": {
            "label": "cherry",
            "direction": "outbound",
            "pipIndex": 0
        }
    }

    // clItems.connectNodes(connectEvent)

    let ordered = {
        "sender": {
            "label": "apples",
            "direction": "outbound",
            "pipIndex": 0
        },
        "receiver": {
            "label": "cherry",
            "direction": "inbound",
            "pipIndex": 0
        }
    }

    clItems.connectNodes(ordered)
}


const app = createMiniApp();

const backLayer = new CanvasLayer('.canvas-container.back canvas')
const foreLayer = new CanvasLayer('.canvas-container.fore canvas')
const clItems = new CanvasLayerGroup(backLayer, foreLayer)

