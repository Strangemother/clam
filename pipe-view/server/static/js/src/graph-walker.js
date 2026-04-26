class GraphWalker {
	constructor(conf={}) {
		this.connections = conf.connections || pipeData.connections
		this.windows = conf.windows || app.windowMap
	}

	getConnections(name) {
		if(name == undefined) {
			return []
		}

		let res = []
		for(let connectionId in this.connections) {
			let connection = this.connections[connectionId]
			if(connection == undefined || connection.obj == undefined) {
				continue
			}

			let senderLabel = connection.obj.sender?.label
			let receiverLabel = connection.obj.receiver?.label

			if(senderLabel == name || receiverLabel == name) {
				res.push(connection)
			}
		}

		return res
	}

	getIncomingIds(name) {
		return this.getDirection(name, false)
	}

	getOutgoingIds(name) {
		return this.getDirection(name, true)
	}

	getDirection(name, outbound=true) {
		if(name == undefined) {
			return []
		}

		let res = []
		for(let connectionId in this.connections) {
			let connection = this.connections[connectionId]
			if(connection == undefined || connection.obj == undefined) {
				continue
			}

			let sender = connection.obj?.sender
			let receiver = connection.obj?.receiver

			let outboundLabel = sender?.label
			let inboundLabel = receiver?.label
			if(sender?.direction == 'inbound' && receiver?.direction == 'outbound') {
				outboundLabel = receiver?.label
				inboundLabel = sender?.label
			}

			let sourceLabel = outbound ? outboundLabel : inboundLabel
			let targetLabel = outbound ? inboundLabel : outboundLabel
			if(sourceLabel == name && targetLabel != undefined) {
				res.push(targetLabel)
			}
		}

		return [...new Set(res)]
	}

	createConnection(fromName, toName, senderPipIndex=0, receiverPipIndex=0, line={}) {
		if(fromName == undefined || toName == undefined) {
			return null
		}

		const senderWindow = this.windows[fromName]
		const receiverWindow = this.windows[toName]
		if(senderWindow == undefined || receiverWindow == undefined) {
			console.error('Cannot create connection; unknown window label.', { fromName, toName })
			return null
		}

		const lineConfig = {
			color: line?.color,
			design: line?.design ?? line?.style ?? line?.lineDesign
		}

		const connection = {
			sender: {
				label: fromName,
				direction: 'outbound',
				pipIndex: senderPipIndex
			},
			receiver: {
				label: toName,
				direction: 'inbound',
				pipIndex: receiverPipIndex
			},
			line: lineConfig
		}

		document.dispatchEvent(new CustomEvent('connectnodes', {
			detail: connection
		}))

		return connection
	}

	clearConnections() {
		for(let connectionId in this.connections) {
			delete this.connections[connectionId]
		}

		pipeData.raw.length = 0

		for(let i = 0; i < clItems.layers.length; i++) {
			let layer = clItems.layers[i]
			if(layer.lines != undefined) {
				layer.lines = {}
			}
		}
	}

    getWindow(name) {
        // Returns the window object for the given name, or null if not found.
        if(name == undefined) {
            return null
        }

        const win = this.windows[name]
        return win || null

    }

    getNode(name) {
        // return the app within the node.
        const win = this.getWindow(name)
        if(win == null) {
            return null
        }

        return win.vueApp || null
    }
}


class LocalStorageGraphWalker extends GraphWalker {
	exportJSON(indent=2) {
		let graph = {
			windows: Object.keys(this.windows).map((name) => {
				const win = this.windows[name]
				return { name, x: win.x, y: win.y }
			}),
			connections: []
		}

		for(let connectionId in this.connections) {
			let connection = this.connections[connectionId]
			let obj = connection?.obj
			if(obj == undefined) {
				continue
			}

			let exportedConnection = {
				sender: {
					label: obj.sender?.label,
					direction: obj.sender?.direction || 'outbound',
					pipIndex: obj.sender?.pipIndex ?? 0
				},
				receiver: {
					label: obj.receiver?.label,
					direction: obj.receiver?.direction || 'inbound',
					pipIndex: obj.receiver?.pipIndex ?? 0
				},
				line: {
					color: obj.line?.color,
					design: obj.line?.design
				}
			}

			graph.connections.push(exportedConnection)
		}

		return JSON.stringify(graph, null, indent)
	}

	importJSON(content, replace=true) {
		let graph = content
		if(typeof content == 'string') {
			try {
				graph = JSON.parse(content)
			} catch(error) {
				console.error('Invalid graph JSON payload.', error)
				return null
			}
		}

		if(graph == undefined || typeof graph != 'object') {
			return null
		}

		if(replace) {
			this.clearConnections()
		}

		// Normalise window entries: support both legacy strings and { name, x, y } objects
		const windowEntries = (Array.isArray(graph.windows) ? graph.windows : []).map((entry) =>
			typeof entry === 'string' ? { name: entry } : entry
		)
		const windowMap = new Map(windowEntries.map((e) => [e.name, e]))
		const connections = Array.isArray(graph.connections) ? graph.connections : []

		for(let i = 0; i < connections.length; i++) {
			let connection = connections[i]
			let senderLabel = connection?.sender?.label
			let receiverLabel = connection?.receiver?.label
			if(senderLabel != undefined && !windowMap.has(senderLabel)) {
				windowMap.set(senderLabel, { name: senderLabel })
			}
			if(receiverLabel != undefined && !windowMap.has(receiverLabel)) {
				windowMap.set(receiverLabel, { name: receiverLabel })
			}
		}

		windowMap.forEach((entry) => {
			if(entry.name == undefined || this.windows[entry.name] != undefined) {
				return
			}

			const conf = { name: entry.name }
			if(entry.x != undefined) { conf.x = entry.x }
			if(entry.y != undefined) { conf.y = entry.y }
			app.spawnWindow(conf)
		})

		for(let i = 0; i < connections.length; i++) {
			let connection = connections[i]
			let sender = connection?.sender
			let receiver = connection?.receiver
			let line = connection?.line
			let fromName = sender?.label
			let toName = receiver?.label

			if(fromName == undefined || toName == undefined) {
				continue
			}

			this.createConnection(
				fromName,
				toName,
				sender?.pipIndex ?? 0,
				receiver?.pipIndex ?? 0,
				line
			)
		}

		return graph
	}

	saveToLocalStorage(storageKey='pipe-view-graph') {
		const json = this.exportJSON()
		localStorage.setItem(storageKey, json)
		return json
	}

	restoreFromLocalStorage(storageKey='pipe-view-graph', replace=true) {
		const json = localStorage.getItem(storageKey)
		if(json == null) {
			return null
		}

		return this.importJSON(json, replace)
	}

	/* Reads saved window positions from localStorage and moves any already-open
	   windows to their stored x/y. If the key does not exist, does nothing. */
	restorePositions(storageKey='pipe-view-graph') {
		const json = localStorage.getItem(storageKey)
		if(json == null) {
			return
		}

		let graph
		try {
			graph = JSON.parse(json)
		} catch(error) {
			console.error('restorePositions: invalid JSON', error)
			return
		}

		const entries = Array.isArray(graph?.windows) ? graph.windows : []
		for(const entry of entries) {
			if(typeof entry !== 'object' || entry.x == undefined || entry.y == undefined) {
				continue
			}
			const win = this.windows[entry.name]
			if(win != undefined) {
				win.move(entry.x, entry.y)
			}
		}
	}
}


