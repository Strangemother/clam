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

		const sourceKey = outbound ? 'sender' : 'receiver'
		const targetKey = outbound ? 'receiver' : 'sender'
		let res = []
		for(let connectionId in this.connections) {
			let connection = this.connections[connectionId]
			if(connection == undefined || connection.obj == undefined) {
				continue
			}

			let sourceLabel = connection.obj[sourceKey]?.label
			if(sourceLabel == name) {
				let targetLabel = connection.obj[targetKey]?.label
				if(targetLabel != undefined) {
					res.push(targetLabel)
				}
			}
		}

		return [...new Set(res)]
	}

	createConnection(fromName, toName, senderPipIndex=0, receiverPipIndex=0) {
		if(fromName == undefined || toName == undefined) {
			return null
		}

		const senderWindow = this.windows[fromName]
		const receiverWindow = this.windows[toName]
		if(senderWindow == undefined || receiverWindow == undefined) {
			console.error('Cannot create connection; unknown window label.', { fromName, toName })
			return null
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
			}
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

}

class LocalStorageGraphWalker extends GraphWalker {
	exportJSON(indent=2) {
		let graph = {
			windows: Object.keys(this.windows),
			connections: []
		}

		for(let connectionId in this.connections) {
			let connection = this.connections[connectionId]
			let obj = connection?.obj
			if(obj == undefined) {
				continue
			}

			graph.connections.push({
				sender: {
					label: obj.sender?.label,
					direction: obj.sender?.direction || 'outbound',
					pipIndex: obj.sender?.pipIndex ?? 0
				},
				receiver: {
					label: obj.receiver?.label,
					direction: obj.receiver?.direction || 'inbound',
					pipIndex: obj.receiver?.pipIndex ?? 0
				}
			})
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

		const windowNames = new Set(Array.isArray(graph.windows) ? graph.windows : [])
		const connections = Array.isArray(graph.connections) ? graph.connections : []

		for(let i = 0; i < connections.length; i++) {
			let connection = connections[i]
			let senderLabel = connection?.sender?.label
			let receiverLabel = connection?.receiver?.label
			if(senderLabel != undefined) {
				windowNames.add(senderLabel)
			}
			if(receiverLabel != undefined) {
				windowNames.add(receiverLabel)
			}
		}

		windowNames.forEach((name)=>{
			if(name == undefined || this.windows[name] != undefined) {
				return
			}

			app.spawnWindow({ name })
		})

		for(let i = 0; i < connections.length; i++) {
			let connection = connections[i]
			let sender = connection?.sender
			let receiver = connection?.receiver
			let fromName = sender?.label
			let toName = receiver?.label

			if(fromName == undefined || toName == undefined) {
				continue
			}

			this.createConnection(
				fromName,
				toName,
				sender?.pipIndex ?? 0,
				receiver?.pipIndex ?? 0
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
}


window.GraphWalker = LocalStorageGraphWalker
