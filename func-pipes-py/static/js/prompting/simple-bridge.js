// const edgesRegistry = {}
// const pipRegistry = {}


class SimpleBridge {

    /* Requires callWaitingEvents() to pump the stack*/
    eventsMode = true

    constructor(panelRegistry={}){
        this.edgesRegistry = {}
        this.pipRegistry = {}

        this.panelRegistry = panelRegistry

        this._waitingEvents = []
        this._autoRunEvents = false;
        window.addEventListener('noderesult', this.noderesultEventListener.bind(this))
    }

    getCompass() {
        return {
            'in': 'out',
            'out': 'in'
        }
    }

    getInverseDirection(v) {
        return this.getCompass()[v]
    }


    resolvePipDescriptor(node) {
        const panel = this.panelRegistry[node?.id]
        if(panel == undefined) {
            return null
        }

        const inboundIndex = panel.pipsInbound.findIndex((pip) => pip.name == node.pip)
        if(inboundIndex > -1) {
            return {
                label: node.id,
                direction: 'inbound',
                pipIndex: inboundIndex,
            }
        }

        const outboundIndex = panel.pipsOutbound.findIndex((pip) => pip.name == node.pip)
        if(outboundIndex > -1) {
            return {
                label: node.id,
                direction: 'outbound',
                pipIndex: outboundIndex,
            }
        }

        return null
    }

    emitVisualConnection(fromNode, toNode, meta) {

        const sender = this.resolvePipDescriptor(fromNode)
        const receiver = this.resolvePipDescriptor(toNode)

        if(sender == undefined || sender == null || receiver == undefined || receiver == null) {
            return
        }

        dispatchEvent('connectnodes', {
                sender,
                receiver,
                line: Object.assign({
                    color: '#5588ff',
                    design: 's-curve',
                    width: 2,
                }, meta?.line || {}),
            }, document)

        if(typeof dispatchRequestDrawEvent == 'function') {
            requestAnimationFrame(() => dispatchRequestDrawEvent())
        }
    }

    connectMany(...connections) {
        connections.forEach((c)=>{
            if(typeof(c[0]) == 'string') {
                this.easyConnectPips(c[0], c[1], c[2])
            } else {
                this.connectPips(c[0], c[1], c[2])
            }
        })
    }

    easyConnectPips(fromId, toId, meta) {
        return this.connectPips(
                { id: fromId, pip: 'out' },
                { id: toId, pip: 'in'},
                meta
            )
    }
    /* A graph but without the name.*/
    connectPips(fromNode, toNode, meta) {
        let fromName = `${fromNode.id}:${fromNode.pip}`
        let toName = `${toNode.id}:${toNode.pip}`
        let name = `${fromName}-${toName}`
        console.log('Connection', name)

        /* Add to the edge to edge.*/
        this.edgesRegistry[name] = {
            fromNode,
            toNode,
            meta
        }

        let fromDict = this.pipRegistry[fromName] || { to: new Set, from: new Set}
        let toDict = this.pipRegistry[toName] || { to: new Set, from: new Set}

        fromDict.to.add(toNode)
        toDict.from.add(fromNode)

        this.pipRegistry[fromName] = fromDict
        this.pipRegistry[toName] = toDict

        this.emitVisualConnection(fromNode, toNode, meta)
    }

    callNodeEvented(targetNode, data) {
        /* Call a node, with the results flowing through as events

            targetNode = {
                id: nodeId
                pip: pipName
            }
            data = {}

        then it dispatches an event, of which is picked up and moved
        */
       // get node
        let destNode = targetNode
        let destPip = undefined

        if(Array.isArray(targetNode)) {
            // node, origin pip
            destNode = targetNode[0]
            destPip = targetNode[1]
        }
       let node = panelRegistry[destNode.id]
       // call with pip index
       let cleanValue = node.graphExecute(data, destPip?.pip || destNode?.pip || 'in')
       // emit result.
       this.emitResult(cleanValue, destNode)
       // The node result is collected elsewhere and continued.
    }

    emitResult(cleanValue, originNode) {
        /* dispatch the standard node result event

        originNode contains the id and pip used for this cleanValue.

            originNode = {
                id: nodeId
                pip 'in'
            }
            cleanValue = 'result from in->callback'

        */
        let pip = this.getInverseDirection(originNode.pip || 'in')
        let detail = {
                    id: originNode.id
                    // At the moment, a noderesult emits from _out_.
                    , pip: 'out' // this.getInverseDirection(originNode.pip || 'in')
                    , value: cleanValue
                }
        // let e = new CustomEvent('noderesult', { detail })

        console.log('dispatchEvent', detail)
        // window.dispatchEvent(e)
        dispatchEvent('noderesult', detail)
    }

    emitResultThrough(cleanValue, originNode) {
        /* dispatch the standard node result event _through_ the originNode.
        For example to send {out}

        originNode contains the id and pip used for this cleanValue.

            originNode = {
                id: nodeId
                pip 'in'
            }
            cleanValue = 'result from in->callback'

        */
        let detail = {
                    id: originNode.id
                    , pip: originNode.pip
                    , value: cleanValue
                }

        // let e = new CustomEvent('noderesult', { detail })

        console.log('dispatchEvent', detail)
        // window.dispatchEvent(e)
        dispatchEvent('noderesult', detail)
    }

    noderesultEventListener(event) {
        /* An event in to continue the chain down the edge. */
        let detail = event.detail
        console.log('noderesult EventListener', detail)
        /* Get pip next node.*/
        let nextNodesAndPips = this.getNext(detail, true);
        console.log('next', nextNodesAndPips)
        this.callNodesEvented(nextNodesAndPips, detail.value)
    }

    callNodesEvented(targetNodeList, data) {
        /* Call many next nodes - calling callNodeEvented iteratively. */

        /*
            this is very useful. We can switch to from an immediate
            mode to an event mode.

            The event mode `callWaitingEvents` iterates the same
            expected objects.
         */
        if(this.eventsMode) {
            targetNodeList.forEach((n)=>this._waitingEvents.push([n, data]))
        } else {
            targetNodeList.forEach((n)=>this.callNodeEvented(n, data))
        }
    }

    emitWaitingCount(){
        // window.dispatchEvent(new CustomEvent('waitingcount', {
        //     detail: {count: this._waitingEvents.length}
        // }))
        dispatchEvent('waitingcount', {count: this._waitingEvents.length})

    }

    autoRunEvents(on=true) {
        this._autoRunEvents = on
        this.callWaitingEvents()
    }

    callWaitingEvents(){
        /*
        Read the list of events, pushed in the last step of the
        event loop.

        Each event is pushed as expected. The next nodes are called -
        of which stack waiting events for a forever filling stack.

        At the moment it iterates all events, but this could be easily
        split into chunks or timely delayed.

        This is a keypoint for mergeNode functionality.
        */
        let events = this._waitingEvents
        this._waitingEvents = []

        events.forEach((item)=>{
            this.callNodeEvented(item[0], item[1])
        });

        this.emitWaitingCount()

        if(this.eventsMode) {
            if(this._autoRunEvents){
                setTimeout(()=>this.callWaitingEvents(), 300)
            }
        }

        if( this._waitingEvents.length == 0) {
            console.info('End Graphs.')
        } else {
            if(this.eventsMode) {

                console.info('simpleBridge.callWaitingEvents()')
            }
        }
    }

    getNext(fromNode, withPip=false) {
        /* return the next pip from the given pip

            getNext({
                id: nodeId
                pip: pipName
            })
            <Node>
        */
        let fromName = `${fromNode.id}:${fromNode.pip}`
        let fromDict = this.pipRegistry[fromName]
        let res = []

        fromDict?.to?.forEach((toNode)=>{
            // Resolve each object
            if(withPip) {
                res.push([panelRegistry[toNode.id], toNode])
                return
            }
            res.push(panelRegistry[toNode.id])
        })

        return res
    }
}


