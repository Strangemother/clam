/*
A wrapper of the winbox app to bind a vue app to the winbox view.

Every winbox window generates a new vue app
Pip drags are handled here - emitting events to the pipes managers.
*/

const cache = {}

const reactive = PetiteVue.reactive



const dispatchRequestDrawEvent = function(data={}){
    document.dispatchEvent(new CustomEvent('requestdraw', {
        detail: data
    }))
}

const dispatchFocusNodeEvent = function(data={}){
    document.dispatchEvent(new CustomEvent('focusnode', {
        detail: data
    }))
}


const listenEvent = function(name, callback, opts={ passive: true }) {
    document.addEventListener(name, callback, opts)
}



const createWinboxVueApp = function(windowApp, conf) {
    /* Ran by the app `pipes-ui-app.js`

        let _window = new WinBox(name, winappObj);
        createWinboxVueApp(_window, conf)

    Then we create a vue app for the internal.
    This exists within the `winbox.vueApp`

    These methods are available on the vueApp.

    This app handles the UI dragging from tip to tip
    and view data.
    */
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
            let cols = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8',
                        '#f58231', '#911eb4', '#46f0f0', '#f032e6',
                        ]
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



const runPipes = function(conf) {
    /* A run-all function for the tool. One ran, pipes is ready to use.

    - create canvas layers
    - create group tool
    - spawn addons (dragging, utils)
    */
   let backName = conf.backLayerSelector || '.canvas-container.back canvas'
   let foreName = conf.foreLayerSelector || '.canvas-container.fore canvas'

    const backLayer = new CanvasLayer(backName)
    const foreLayer = new CanvasLayer(foreName)

    // dirty for now.
    const clItems = new CanvasLayerGroup(backLayer, foreLayer)
    window.clItems = clItems


    // Drag and zoom functionality.
    const infiniteDrag = new WinboxInfiniteDrag(conf.dragspaceSelector || 'main')

    /* Convenience tool. */
    const pipesTool = new PipesTool();
    window.pipesTool = pipesTool
}

