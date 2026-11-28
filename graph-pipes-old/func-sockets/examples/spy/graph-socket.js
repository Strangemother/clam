/** Browser client for one graph room on a Func Sockets relay. */
class GraphSocket extends EventTarget {
    constructor(graphId, baseUrl = 'ws://127.0.0.1:8777') {
        super()
        this.graphId = graphId
        this.baseUrl = baseUrl.replace(/\/$/, '')
        this.socket = null
    }

    connect() {
        const graphId = encodeURIComponent(this.graphId)
        this.socket = new WebSocket(`${this.baseUrl}/graph/${graphId}`)
        this.socket.addEventListener('open', () => this.dispatchEvent(new Event('open')))
        this.socket.addEventListener('close', () => this.dispatchEvent(new Event('close')))
        this.socket.addEventListener('error', () => this.dispatchEvent(new Event('error')))
        this.socket.addEventListener('message', (event) => {
            let value = event.data
            if (typeof value === 'string') {
                try {
                    value = JSON.parse(value)
                } catch (error) {
                    // Non-JSON text is valid relay traffic.
                }
            }
            this.dispatchEvent(new CustomEvent('message', { detail: value }))
        })
        return this.socket
    }

    send(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            throw new Error('GraphSocket is not connected')
        }
        this.socket.send(typeof message === 'string' ? message : JSON.stringify(message))
    }

    bind(graphId) {
        this.graphId = graphId
        this.send({ type: 'bind', graph_id: graphId })
    }

    close() {
        this.socket?.close()
    }
}
