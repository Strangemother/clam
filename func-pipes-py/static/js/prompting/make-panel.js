
const makePanel = function(extra={}) {
     let d = Object.assign({
        pipsInbound: [
            { name: 'in'},
        ]
        , pipsOutbound: [
            { name: 'out'},
        ]

        , viewData: Vue.ref({ value: -1 })
        , pipData: {}
        , type: 'text-input'
        , funcName: ''

        , getPipConf(name) {
            const inboundIndex = this.pipsInbound.findIndex((pip) => pip.name == name)
            if(inboundIndex > -1) {
                 return this.pipsInbound[inboundIndex]
            }
            const outboundIndex = this.pipsOutbound.findIndex((pip) => pip.name == name)
            if(outboundIndex > -1) {
                 return this.pipsInbound[outboundIndex]
            }

        }

        , graphExecute(data, throughPip) {
            /* A standard execution of the node function,
            from the graph, e.g. callNodeEvented.

            Run and return a clean value
            */
            // Here we dispatch to the internal handler
            // or data store.
            let pip = this.getPipConf(throughPip)
            if(!pip) {
                console.warn('No pip', throughPip)
            } else {

                    if(pip.store != false) {
                        this.pipData[throughPip] = data
                    }
                    if(pip.execute == false) {
                        console.log("Pip doesn't execute")
                        return
                    }
            }

            return this.callback(data, throughPip)
        }
        , callback(data, pip) {
            console.log('generic node call', this.id, data, pip)

            const viewComponent = this.getViewComponent()
            const customResult = viewComponent?.customCallback(data, pip)

            this.viewData.value.value = customResult

            return customResult
        }
        , id: Math.random().toString(32).slice(3)
        , _viewComponent: null
        , getViewComponent(){
            return this._viewComponent
        }

        , getPosition() {

            let style = this._viewElement.style
            return {
                top: parseFloat(style.top)
                , left: parseFloat(style.left)
                , width: parseFloat(style.width)
                , height: parseFloat(style.height)
            }
        }
    }, extra)

    return d;
}
