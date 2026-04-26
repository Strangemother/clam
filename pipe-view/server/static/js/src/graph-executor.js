/*

The GraphExecutor extends LocalStorageGraphWalker to provide _execution_ methods.

- Call to run code setup on a node
- Each step is a call to `executeNode(name, data)`
- then it steps to the next nodes

 */

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
        let taskFunc = this.taskMap[taskName] || this.taskMap['defaultTask']
        taskFunc = taskFunc.bind(this.taskMap)
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

