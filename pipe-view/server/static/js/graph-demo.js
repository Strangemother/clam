
class WorkTasks {
    /*
    This is a scratch area for testing out code related to graph traversal and highlighting, demo graph setup, and the PipesTool wrapper class. It's not meant to be a permanent part of the codebase, but it can be useful for iterating on these features in the context of the full app before deciding what to keep and what to discard.
    */
    constructor(){
        console.log('WorkTasks initialized')
    }

    banana(config, data) {
        console.log('Banana task executed', config)
        return data + 2
    }

    cherry(){
        console.log('cherry');
        return 2
    }
    date(){
        console.log('date');
        return 2
    }
    elderberry(){
        console.log('elderberry');
        return 2
    }
    fig(){
       console.log('fig');
       return 2 
    }
    grape(){
        console.log('grape');
        return 2
    }
    honeydew(){
        console.log('honeydew');
        return 2
    }
    kiwi(){
        console.log('kiwi');
        return 2
    }
    lemon(){
        console.log('lemon');
        return 2
    }

    defaultTask(config) {
        // If a task is not coded, this is executed. 
        console.log('Default task executed', config)
    }
}
    

const spawnDemoWindows = function(appRef) {
    if(appRef == undefined) {
        return
    }

    const randomPercent = function(max=80) {
        return `${Math.floor(Math.random() * (max + 1))}%`
    }

    let nodes = [
        { name: 'apples', x: 60, y: 60 }
        , { name: 'banana', exampleData: 123 }
        , { name: 'cherry'}
        , { name: 'date'}
        , { name: 'elderberry'}
        , { name: 'fig'}
        , { name: 'grape'}
        , { name: 'honeydew'}
        , { name: 'kiwi'}
        , { name: 'lemon'}
    ]

    nodes.forEach((item)=>{
        appRef.spawnWindow(
            Object.assign({    
                x: randomPercent()
                , y: randomPercent()
            }, item)
        )
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
    // setTimeout(()=>{
    //     autoConnectDemoNodes(layerGroup)
    // }, 300)
}


class GraphHighlighter {

    constructor(conf={}) {
        this.app = conf.app || app
        this.walker = conf.walker || new GraphWalker()
        this.highlightClass = conf.highlightClass || 'node-highlight'
        this.cycleClass = conf.cycleClass || 'node-cycle'
        this._highlighted = new Set()
        this._cycleFrontier = []
        this._cyclePrev = null
        this._cycleStart = null
        this._cycleStarted = false
        this._runTimer = null
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

    /* Sets up a walk starting from node. Each stepLights() call dynamically
       computes the next frontier from the current one, so cycles are followed
       naturally rather than being cut off at setup time. */
    cycleFrom(node) {
        this.clearCycle()
        this._cycleStart = node
        this._cycleFrontier = [node]
        this._cyclePrev = null
        this._cycleStarted = false
    }

    /* Advances the cycle by one frontier level:
       - Removes the cycle class from the previous frontier.
       - Applies the cycle class to every node in the current frontier.
       - Computes the next frontier from outgoing connections (live, no
         cross-step visited tracking, so loops are followed naturally).
       wrap=false (default): stops only when the next frontier is empty,
         i.e. all branches have genuinely no outgoing connections.
       wrap=true: when all branches terminate, resets to the start node. */
    stepLights(wrap=false) {
        if(this._cycleFrontier.length === 0) { return }

        // Remove previous frontier's class
        if(this._cyclePrev) {
            for(const name of this._cyclePrev) {
                const win = this._getWin(name)
                if(win) { win.removeClass(this.cycleClass) }
            }
        }

        // Light the current frontier
        for(const name of this._cycleFrontier) {
            const win = this._getWin(name)
            if(win) { win.addClass(this.cycleClass) }
        }

        // Compute next frontier dynamically from outgoing connections
        const seen = new Set()
        const nextFrontier = []
        for(const name of this._cycleFrontier) {
            const outgoing = this.walker.getOutgoingIds(name)
            for(const next of outgoing) {
                if(!seen.has(next)) {
                    seen.add(next)
                    nextFrontier.push(next)
                }
            }
        }

        this._cyclePrev = this._cycleFrontier
        this._cycleStarted = true

        if(nextFrontier.length === 0) {
            // No outgoing connections — all branches are terminal
            this._cycleFrontier = wrap ? [this._cycleStart] : []
        } else {
            this._cycleFrontier = nextFrontier
        }
    }

    /* Returns true if the cycle has a non-empty frontier to advance through. */
    _hasCycleSteps() {
        return this._cycleFrontier.length > 0
    }

    /* Runs the full cycle from node automatically, advancing one BFS level per
       interval until no steps remain, then stops.
       options.delay   — ms between steps (default 400)
       options.wrap    — whether to loop indefinitely (default false)
       options.onDone  — optional callback fired when sequence ends */
    runLights(node, options={}) {
        const delay = options.delay ?? options.timeout ?? 400
        const wrap = options.wrap ?? false
        const onDone = options.onDone

        this.stopLights()
        this.cycleFrom(node)

        const tick = () => {
            this.stepLights(wrap)
            if(!wrap && !this._hasCycleSteps()) {
                this._runTimer = null
                if(onDone) { onDone() }
                return
            }
            this._runTimer = setTimeout(tick, delay)
        }

        this._runTimer = setTimeout(tick, delay)
    }

    /* Cancels a running runLights sequence. */
    stopLights() {
        if(this._runTimer != null) {
            clearTimeout(this._runTimer)
            this._runTimer = null
        }
    }

    /* Removes cycle class from all active frontier nodes and resets state. */
    clearCycle() {
        for(const group of [this._cyclePrev, this._cycleFrontier]) {
            if(!group) { continue }
            for(const name of group) {
                const win = this._getWin(name)
                if(win) { win.removeClass(this.cycleClass) }
            }
        }
        this._cycleFrontier = []
        this._cyclePrev = null
        this._cycleStart = null
        this._cycleStarted = false
    }
}

class GraphExecutor extends LocalStorageGraphWalker {
    // Walk with code execution
    constructor(conf={}) {
        super(conf)
        this.taskMap = conf.taskMap || {}
    }

    executeNode(nodeName, data) {
        const node = this.getNode(nodeName)
        if(node == null) {
            console.warn(`No node found with name ${nodeName}`)
            return
        }

        const taskName = nodeName // node.task || 'default'
        const taskFunc = this.taskMap[taskName] || this.taskMap['defaultTask']
        if(typeof taskFunc !== 'function') {
            console.warn(`No task function found for task ${taskName} on node ${nodeName}`)
            return
        }

        try {
            let result = taskFunc(node, data)
            return result;

        } catch (err) {
            console.error(`Error executing task ${taskName} for node ${nodeName}:`, err)
        }

    }

    executeAndExpected(nodeName, data) {
        const result = this.executeNode(nodeName, data)
        return [result, this.getOutgoingIds(nodeName)]
    }

    executeLoop(nodeName, data, options={}) {
        /* Execute the node with the data, then schedule each downstream node
        on a timer — one step per tick. Returns a controller so the caller can
        stop the chain or adjust the speed mid-run.

            const chain = executor.executeLoop('apples', myData)
            chain.setDelay(500)   // speed up to 500ms
            chain.stop()          // cancel all pending steps
        */

        // conf is shared across all branches of this chain so setDelay()
        // affects every in-flight branch immediately.
        const conf = { delay: options.delay ?? 1000 }

        // All pending timeout IDs — stop() drains this to cancel the chain.
        const timers = new Set()

        const step = (nodeName, data) => {
            const [result, nextIds] = this.executeAndExpected(nodeName, data)
            if(nextIds.length === 0) {
                // Terminal node — valid end of a pipeline branch.
                return
            }

            /*
            For each outgoing connection, execute the next node with the result as input.
            Note: Parallel execution must exist.
            Therefore each result is fed into its own connections.        
                
                a => b -> e
                     c -> d -> f 
                               g
            
            Data between b -> e is separate from c -> d -> f -> g.
            
            */

            for(const nextId of nextIds) {
                // When branching, each child gets its own deep copy of result so
                // mutations in one pipeline branch cannot corrupt another.
                // Primitives are passed as-is (copy-by-value already).
                const branchData = (nextIds.length > 1 && result !== null && typeof result === 'object')
                    ? structuredClone(result)
                    : result

                const id = setTimeout(() => {
                    timers.delete(id)
                    step(nextId, branchData)
                }, conf.delay)

                timers.add(id)
            }
        }

        // Execute the entry node immediately, then let the timer drive the rest.
        step(nodeName, data)

        return {
            stop() {
                for(const id of timers) { clearTimeout(id) }
                timers.clear()
            },
            setDelay(ms) { conf.delay = ms }
        }
    }

}

class PipesTool {
    //  user tool to access all the bits easily.
    filename = 'pipes-tool-graph'
    constructor(conf={}) {
        this.app = conf.app || app
        this.walker = conf.walker || new GraphExecutor({ taskMap: new WorkTasks() })
        this.lights = new GraphHighlighter({ app: this.app, walker: this.walker })
        this.layerGroup = conf.layerGroup || clItems
    }

    draw(){
        this.layerGroup.draw.apply(this.layerGroup, arguments)
    }


    save(name = this.filename) {
        // simple save method 
        this.walker.saveToLocalStorage(name)
    }

    restore(name = this.filename) {
        this.walker.restoreFromLocalStorage(name)
        this.walker.restorePositions(name)
        setTimeout(() => {
            this.draw()    
        }, 300);
    }

    animDraw(){
        this.layerGroup.animDraw()
    }
}

const pipesTool = new PipesTool();


window.PipesTool = PipesTool
window.pipesTool = pipesTool
window.GraphHighlighter = GraphHighlighter
window.bootDemoGraph = bootDemoGraph
window.spawnDemoWindows = spawnDemoWindows
window.autoConnectDemoNodes = autoConnectDemoNodes

bootDemoGraph()
