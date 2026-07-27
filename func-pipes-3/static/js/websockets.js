class BackendSocket {
    constructor(url = `ws://127.0.0.1:8777/graph/func-pipes-3`) {
        this.url = url
        this.socket = null
        this.messageHandlers = []
        this.onStatus = () => {}
    }

    onMessage(handler) {
        this.messageHandlers.push(handler)
        return this
    }

    connect(url = this.url) {
        this.close()
        this.url = url
        this.onStatus('connecting')
        this.socket = new WebSocket(this.url)
        this.socket.addEventListener('open', () => this.onStatus('connected'))
        this.socket.addEventListener('message', (event) => {
            let command = event.data
            try {
                command = JSON.parse(event.data)
            } catch {
                // Preserve non-JSON messages for the hook.
            }
            this.messageHandlers.forEach((handler) => handler(command))
        })
        this.socket.addEventListener('close', () => {
            this.socket = null
            this.onStatus('disconnected')
        })
        this.socket.addEventListener('error', () => this.onStatus('error'))
        return this.socket
    }

    send(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            throw new Error('WebSocket is not connected')
        }
        this.socket.send(typeof message === 'string' ? message : JSON.stringify(message))
    }

    close() {
        if (this.socket) this.socket.close()
        this.socket = null
        this.onStatus('disconnected')
    }
}
