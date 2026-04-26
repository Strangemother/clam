const spawnDemoWindows = function(appRef) {
    if(appRef == undefined) {
        return
    }

    const randomPercent = function(max=80) {
        return `${Math.floor(Math.random() * (max + 1))}%`
    }

    let names = [
        'apples',
        'banana',
        'cherry',
        'date',
        'elderberry',
        'fig',
        'grape',
        'honeydew',
        'kiwi',
        'lemon'
    ]

    names.forEach((name)=>{
        appRef.spawnWindow({
            name,
            x: randomPercent(),
            y: randomPercent()
        })
    })
}


const autoConnectDemoNodes = function(layerGroup) {
    if(layerGroup == undefined) {
        return
    }

    let ordered = {
        sender: {
            label: 'apples',
            direction: 'outbound',
            pipIndex: 0
        },
        receiver: {
            label: 'cherry',
            direction: 'inbound',
            pipIndex: 0
        }
    }

    layerGroup.connectNodes(ordered)
}


const bootDemoGraph = function(appRef=app, layerGroup=clItems) {
    if(appRef == undefined || layerGroup == undefined) {
        return
    }

    spawnDemoWindows(appRef)
    setTimeout(()=>{
        autoConnectDemoNodes(layerGroup)
    }, 300)
}



bootDemoGraph()


window.bootDemoGraph = bootDemoGraph
window.spawnDemoWindows = spawnDemoWindows
window.autoConnectDemoNodes = autoConnectDemoNodes


class GraphHighlighter {

    constructor(conf={}) {
        this.app = conf.app || app
        this.walker = conf.walker || new GraphWalker()
        this.highlightClass = conf.highlightClass || 'node-highlight'
        this.cycleClass = conf.cycleClass || 'node-cycle'
        this._highlighted = new Set()
        this._cycleQueue = []
        this._cycleIndex = 0
        this._cycleStarted = false
    }

    _getWin(name) {
        return this.app.windowMap[name]
    }

    /* Adds the highlight class to the named node's window. */
    highlight(node) {
        const win = this._getWin(node)
        if(win == undefined) { return }
        win.addClass(this.highlightClass)
        this._highlighted.add(node)
    }

    /* Removes the highlight class from all currently highlighted nodes. */
    clearHighlights() {
        for(const name of this._highlighted) {
            const win = this._getWin(name)
            if(win) { win.removeClass(this.highlightClass) }
        }
        this._highlighted.clear()
    }

    /* Clears all highlights then lights up only the given node. */
    oneLight(node) {
        this.clearHighlights()
        this.highlight(node)
    }

    /* Sets up a walk starting from node, collecting reachable nodes via BFS.
       Call stepLights() repeatedly to walk through them. */
    cycleFrom(node) {
        this.clearCycle()

        const visited = new Set()
        const queue = [node]
        const order = []

        while(queue.length > 0) {
            const current = queue.shift()
            if(visited.has(current)) { continue }
            visited.add(current)
            order.push(current)
            const outgoing = this.walker.getOutgoingIds(current)
            for(const next of outgoing) {
                if(!visited.has(next)) { queue.push(next) }
            }
        }

        this._cycleQueue = order
        this._cycleIndex = 0
        this._cycleStarted = false
    }

    /* Advances the cycle by one node, lighting the current and un-lighting
       the previous. Does not affect regular highlights. */
    stepLights() {
        if(this._cycleQueue.length === 0) { return }

        if(this._cycleStarted) {
            const prevIndex = (this._cycleIndex - 1 + this._cycleQueue.length) % this._cycleQueue.length
            const prev = this._cycleQueue[prevIndex]
            const prevWin = this._getWin(prev)
            if(prevWin) { prevWin.removeClass(this.cycleClass) }
        }

        const current = this._cycleQueue[this._cycleIndex]
        const win = this._getWin(current)
        if(win) { win.addClass(this.cycleClass) }

        this._cycleIndex = (this._cycleIndex + 1) % this._cycleQueue.length
        this._cycleStarted = true
    }

    /* Removes cycle class from all nodes in the current cycle and resets state. */
    clearCycle() {
        for(const name of this._cycleQueue) {
            const win = this._getWin(name)
            if(win) { win.removeClass(this.cycleClass) }
        }
        this._cycleQueue = []
        this._cycleIndex = 0
        this._cycleStarted = false
    }
}


window.GraphHighlighter = GraphHighlighter
