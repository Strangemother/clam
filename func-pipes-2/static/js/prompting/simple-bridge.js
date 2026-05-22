const edgesRegistry = {}
const pipRegistry = {}


class SimpleBridge {

    constructor(panelRegistry={}){
        this._waitingEvents = []
        this.panelRegistry = panelRegistry
        window.addEventListener('noderesult', this.noderesultEventListener.bind(this))

    }

    easyConnectPips(fromId, toId, meta) {
        return this.connectPips(
                { id: fromId, pip: 'out' },
                { id: toId, pip: 'in'},
                meta
            )
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

        document.dispatchEvent(new CustomEvent('connectnodes', {
            detail: {
                sender,
                receiver,
                line: Object.assign({
                    color: '#5588ff',
                    design: 's-curve',
                    width: 2,
                }, meta?.line || {}),
            }
        }))

        if(typeof dispatchRequestDrawEvent == 'function') {
            requestAnimationFrame(() => dispatchRequestDrawEvent())
        }
    }

    /* A graph but without the name.*/
    connectPips(fromNode, toNode, meta) {
        let fromName = `${fromNode.id}:${fromNode.pip}`
        let toName = `${toNode.id}:${toNode.pip}`
        let name = `${fromName}-${toName}`
        console.log('Connection', name)

        /* Add to the edge to edge.*/
        edgesRegistry[name] = {
            fromNode,
            toNode,
            meta
        }

        let fromDict = pipRegistry[fromName] || { to: new Set, from: new Set}
        let toDict = pipRegistry[toName] || { to: new Set, from: new Set}

        fromDict.to.add(toNode)
        toDict.from.add(fromNode)

        pipRegistry[fromName] = fromDict
        pipRegistry[toName] = toDict

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
       let node = panelRegistry[targetNode.id]
       // call with pip index
       let cleanValue = node.graphExecute(data, targetNode.pip || 'in')
       // emit result.
       this.emitResult(cleanValue, targetNode)
       // The node result is collected elsewhere and continued.
    }

    emitResult(cleanValue, targetNode) {
        /* dispatch the standard node result event

        targetNode contains the id and pip used for this cleanValue.

            targetNode = {
                id: nodeId
                pip 'in'
            }
            cleanValue = 'result from in->callback'

        */
        let detail = {
                    id: targetNode.id
                    , pip: 'out' // At the moment, a noderesult emits from _out_.
                    , value: cleanValue
                }
        let e = new CustomEvent('noderesult', { detail })

        console.log('dispatchEvent', detail)
        window.dispatchEvent(e)
    }

    noderesultEventListener(event) {
        /* An event in to continue the chain down the edge. */
        let detail = event.detail
        console.log('noderesult EventListener', detail)
        /* Get pip next node.*/
        let nextNodes = this.getNext(detail);
        console.log('next', nextNodes)
        this.callNodesEvented(nextNodes, detail.value)
    }

    /* Requires callWaitingEvents() to pump the stack*/
    eventsMode = true

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
        window.dispatchEvent(new CustomEvent('waitingcount', {
            detail: {count: this._waitingEvents.length}
        }))
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

        if( this._waitingEvents.length == 0) {
            console.info('End Graphs.')
        } else {
            if(this.eventsMode) {
                console.info('simpleBridge.callWaitingEvents()')
            }
        }
    }

    getNext(fromNode) {
        /* return the next pip from the given pip

            getNext({
                id: nodeId
                pip: pipName
            })
            <Node>
        */
        let fromName = `${fromNode.id}:${fromNode.pip}`
        let fromDict = pipRegistry[fromName]
        let res = []

        fromDict?.to?.forEach((toNode)=>{
            // Resolve each object
            res.push(panelRegistry[toNode.id])
        })

        return res
    }
}


