/*
  prompting/index.js  (app shell)
  ────────────────────────────────
  Thin entry point — bootstraps the Vue app and composes all method groups.

  Load order in prompting.html:
    nodes.js → prompt-spawn.js → prompt-signal.js → prompt-llm.js →
      prompt-wiring.js → prompt-persist.js → prompt-transform.js →
      prompt-pyfunc.js → prompt-event.js → index.js
*/

const { createApp, nextTick } = Vue

const setupDragging = function() {
    window.dragHost = new DragSolo()
}


const setupZooming = function() {
    window.infiniteDrag = new ZoomableInfiniteDrag('.layer-space', '.panel',
        {
            zoomMode: 'transform',
        });
}

/* live panels by ID */
const panelRegistry = {}

const simpleBridge = new SimpleBridge(panelRegistry);


const vueApp = createApp({

    data() {
        return {
            panels: [],
            available: [],
            selected: '',
            waitingCount: -1
        }
    },

    async mounted() {
        // Models must be fetched manually via the toolbar after setting the endpoint.
        // Prompting uses transform-based zoom so node contents scale without reflow.
        setupDragging()
        setupZooming()

        // setTimeout(()=>{
        //     this.createExample()
        // }, 10)
        // this.createExample2()

        fetch('/nodes/')
            .then((d)=>d.json())
            .then((names)=>{this.available = names})

        // window.addEventListener('nodeselect', this.nodeSelectHandler.bind(this))
        // window.addEventListener('pipclick', this.pipclickHandler.bind(this))
        // window.addEventListener('waitingcount', (e)=> {
        //     this.waitingCount = e.detail.count
        // })

        listenEvent('nodeselect', this.nodeSelectHandler.bind(this))
        listenEvent('pipclick', this.pipclickHandler.bind(this))
        listenEvent('waitingcount', (e)=> {
            this.waitingCount = e.detail.count
        })
    },

    methods: {

        createExample2() {
            let a = this.spawnPanel({ id: 'a', type:'text-input'})
            let b = this.spawnPanel({ id: 'b'})
            simpleBridge.callNodeEvented({ id: 'a', pip: 'in'}, 1)
        }

        , createExample3() {
            const conf = {
                panels: [
                    { id: 'a', type: 'text-input'}
                    , { id: 'b'}
                    , { id: 'c'}
                    , { id: 'd'}
                    , { id: 'e'}
                ]
                , connections: [
                    [
                        { id: 'a', pip: 'out' },
                        { id: 'b', pip: 'in'}
                    ]
                    , ['a', 'c']
                    , ['c', 'd']
                    , ['d', 'e']
                ]
            }

            let a = this.spawnPanels(...conf.panels)

            simpleBridge.connectMany(...conf.connections)

            /* We pretend an inbound event through A, it will execute and
            emit an event.*/
            simpleBridge.callNodeEvented({ id: 'a', pip: 'in'}, 1)
        }

        , createExample() {
            const conf = {
                panels: [
                    { id: 'a', type: 'text-input'}
                    , { id: 'b'}
                    , { id: 'c'}
                    , { id: 'd'}
                    , { id: 'e'}
                ]
            }

            let a = this.spawnPanels(...conf.panels)

            // simpleBridge.connectMany(...conf.connections)

            // connect a out to b  in
            simpleBridge.connectPips(
                    { id: 'a', pip: 'out' },
                    { id: 'b', pip: 'in'}
                )

            simpleBridge.easyConnectPips('a', 'c')
            simpleBridge.easyConnectPips('c', 'd')
            simpleBridge.easyConnectPips('d', 'e')

            let nexts = simpleBridge.getNext({ id: 'a', pip: 'out'})
            console.log(nexts)

            /* We pretend an inbound event through A, it will execute and
            emit an event.*/
            simpleBridge.callNodeEvented({ id: 'a', pip: 'in'}, 1)
        }

        , stepButton() {
            simpleBridge.callWaitingEvents()
        }

        , focusSelect(event, panel){
            // console.log(event, panel)
            // window.dispatchEvent(new CustomEvent('nodeselect', {
            //     detail: {
            //         panel
            //     }
            // }))
            dispatchEvent('nodeselect', { panel })
        }

        , clickConnectButton() {
            // open events.
            if(this.clickConnectEnabled) {
                console.log('already enabled')
                return
            }

            this.clickConnectEnabled = true

            console.log('connect mode enabled')
            // wait
            // // close
        }

        , nodeSelectHandler(ev) {
            // 'nodeselect'
            if(this.clickConnectSelected == undefined) {
                this.clickConnectSelected = []
            }

            if(this.clickConnectEnabled) {
                // If the node is first,
                // the selected pip is 'out'
                // else it's 'in'
                // let node = panelRegistry[ev.detail.panel.id]
                let node = ev.detail.panel
                let direction = 'in'
                if(this.clickConnectSelected.length == 0) {
                    direction = 'out'
                }

                // resolve node pip of direction
                if(this.clickConnectSelected[0]
                    && this.clickConnectSelected[0][0] == node.id) {
                    // oops double click
                    console.log('self to self ignored.')
                    return
                }

                this.addClickConnect(node, direction)
            }
        }

        , addClickConnect(node, direction) {
            console.log('addClickConnect')
            this.clickConnectSelected.push([node.id, direction])
            if(this.clickConnectSelected.length == 2) {
                console.log('Complete', this.clickConnectSelected)
                this.clickConnectEnabled = false;
                this.buildConnection(this.clickConnectSelected)
                this.clickConnectSelected = []
            }
        }

        , buildConnection(clickConnectSelected) {
            console.log(clickConnectSelected)
            let l = clickConnectSelected;
            simpleBridge.connectPips(
                    // { id: a.id, pip: 'out' },
                    { id: l[0][0], pip: l[0][1]},
                    { id: l[1][0], pip: l[1][1]}
                    // { id: b.id, pip: 'in'}
                )
        }

        , pipclickHandler(ev) {
            // 'pipclick'
            console.log('pipclickHandler')
            if(this.clickConnectEnabled) {

                let direction = ev.detail.pip.name
                // refuse pips with the same direction.
                this.addClickConnect(ev.detail.panel, direction)
            }
        }

        , spawnButton(){
            this.spawnPanel()
        }

        , spawnPanels(...panels){
            const r = [];
            panels.forEach((x)=> {
                r.push(this.spawnPanel(x))
            });
            return r
        }
        , spawnPanel(data={}){
            console.log('spawnPanel', this.selected)
            let type = this.selected || 'function-call'

            let d = makePanel({
                type
                , funcName: data.funcName
            })

            Object.assign(d, data)

            panelRegistry[d.id] = d
            this.panels.push(d)

            nextTick(() => {
                const el = this.$refs[`panel-${d.id}`][0]
                stickAll(el)
                dragHost.enable(el)
            })

            return d;
        }
    },

});


for(let k in nodeRegister) {
    vueApp.component(k, nodeRegister[k])
}

const mountedApp = vueApp.mount('#app')
