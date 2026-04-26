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

const createWindowApp = function(windowApp, conf) {

    let WindowAppConf = {
        textStatus: 'No Status'
        , label: windowApp.title
        , pipsInbound: []
        , pipsOutbound: []
        , viewInfo: reactive({ words: "None"})
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
        , randomColor() {
            let cols = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6',]
            return cols[Math.floor(Math.random() * cols.length)]
        }
        , connect(sender, receiver, line={}) {
            // console.log('Connect from', sender, 'to: ', receiver)
            line.color = line.color || this.randomColor()
            document.dispatchEvent(new CustomEvent('connectnodes', {
                    detail: {
                        sender
                        , receiver
                        , line
                    }
                })
            )
        }

        , initConfig() {
            return conf
        }

    }

    const WindowApp = PetiteVue.createApp(WindowAppConf)
    const _app = WindowApp.mount(windowApp.body)

    // Create default pips 0, 0.
    WindowAppConf.addInboundPip()
    WindowAppConf.addOutboundPip()

    windowApp.vueApp = WindowAppConf
};


const dispatchRequestDrawEvent = function(data={}){
    document.dispatchEvent(new CustomEvent('requestdraw', {
        detail: data
    }))
}

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
        , spawnWindow(conf={name: this.newPanelName}) {
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
                }
                ,  onmove: function(x, y){
                    // console.log('Moved to', x, y)
                    dispatchRequestDrawEvent()
                }

            };
            Object.assign(winapp, conf);
            let _window = new WinBox(name, winapp);

            createWindowApp(_window, conf)
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
    return app
};


class MyInfiniteDrag extends ZoomableInfiniteDrag {
    dragComplete() {
        // rebind all winbox move events to trigger a redraw, since the positions have changed
        // winbox.move("center", "center");
        // pipesTool.app.windowMap['apples'].move('100px', '100px')
        for (let winName in pipesTool.app.windowMap) {
            let win = pipesTool.app.windowMap[winName]
            // Read the actual CSS position we moved to, not WinBox's stale internal values.
            const left = parseFloat(win.g.style.left) || 0
            const top = parseFloat(win.g.style.top) || 0
            if(left > 0 && top > 0) {
                // winbox force locks 0,0
                // so only reseat visible windows. Otherwise offscreen windows will be snapped to 0,0.
                win.move(left, top)
            }
        }

    }

    moveAllNodes(scale, prevScale, origin) {
        const ratio = scale / prevScale
        const rect = this.element.getBoundingClientRect()
        const mouseX = origin.x - rect.left
        const mouseY = origin.y - rect.top

        for (let winName in pipesTool.app.windowMap) {
            let win = pipesTool.app.windowMap[winName]
            const left = parseFloat(win.g.style.left) || 0
            const top  = parseFloat(win.g.style.top)  || 0
            if (left === 0 && top === 0) continue  // skip unpositioned windows

            const newLeft   = mouseX + (left   - mouseX) * ratio
            const newTop    = mouseY + (top    - mouseY) * ratio
            const newWidth  = win.g.offsetWidth  * ratio
            const newHeight = win.g.offsetHeight * ratio

            win.move(newLeft, newTop)
            win.resize(newWidth, newHeight)

            const scalePercent = Math.round(scale * 100 / 10) * 10
            win.g.className = win.g.className.replace(/\binf-drag-zoom-scale-\d+\b/g, '')
            win.g.classList.add(`inf-drag-zoom-scale-${scalePercent}`)
        }
    }

}


const app = createMiniApp();

const backLayer = new CanvasLayer('.canvas-container.back canvas')
const foreLayer = new CanvasLayer('.canvas-container.fore canvas')
const clItems = new CanvasLayerGroup(backLayer, foreLayer)

const infiniteDrag = new MyInfiniteDrag('main')