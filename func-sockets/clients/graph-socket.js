/**
 * Browser client for one graph room on a Func Sockets relay.
 *
 * Use this file in the UI to send graph commands and receive backend events.
 * It handles connection and JSON decoding only; it does not update UI state or
 * interpret the command/event language.
 *
 * @example
 * const socket = new GraphSocket('graph-42')
 * socket.addEventListener('message', (event) => graphStore.apply(event.detail))
 * socket.connect()
 */
class GraphSocket extends EventTarget {
    /**
     * Prepare a graph client without opening its connection.
     *
     * @param {string} graphId - Graph room to join.
     * @param {string} [baseUrl='ws://127.0.0.1:8777'] - Relay server URL.
     *
     * @example
     * const socket = new GraphSocket('demo', 'ws://127.0.0.1:8777')
     */
    constructor(graphId, baseUrl = 'ws://127.0.0.1:8777') {
        super()
        this.graphId = graphId
        this.baseUrl = baseUrl.replace(/\/$/, '')
        this.socket = null
    }

    /**
     * Open the WebSocket and forward its lifecycle and message events.
     *
     * Listen for `open`, `close`, `error`, and `message` on this GraphSocket.
     * JSON messages are decoded into `event.detail`; other text and binary
     * values are passed through as received.
     *
     * @returns {WebSocket} The browser WebSocket that was opened.
     *
     * @example
     * socket.addEventListener('open', () => console.log('ready'))
     * socket.connect()
     */
    connect() {
        const graphId = encodeURIComponent(this.graphId)
        this.socket = new WebSocket(`${this.baseUrl}/graph/${graphId}`)
        this.socket.addEventListener('open', (event) => this.dispatchEvent(new Event('open')))
        this.socket.addEventListener('close', (event) => this.dispatchEvent(new Event('close')))
        this.socket.addEventListener('error', (event) => this.dispatchEvent(new Event('error')))
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

    /**
     * Send a command or other application message to peers in this graph.
     *
     * Strings are sent unchanged. Other values are encoded as JSON. Call this
     * only after the `open` event.
     *
     * @param {string|object} message - Payload to relay.
     *
     * @example
     * socket.send({ kind: 'command', name: 'graph.snapshot.get' })
     */
    send(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            throw new Error('GraphSocket is not connected')
        }
        this.socket.send(typeof message === 'string' ? message : JSON.stringify(message))
    }

    /**
     * Move the existing connection to another graph room.
     *
     * The relay replies with a normal `message` event containing
     * `{ type: 'bound', graph_id: graphId }`.
     *
     * @param {string} graphId - New graph room to join.
     *
     * @example
     * socket.bind('graph-43')
     */
    bind(graphId) {
        this.graphId = graphId
        this.send({ type: 'bind', graph_id: graphId })
    }

    /**
     * Close the underlying WebSocket if it exists.
     *
     * @example
     * socket.close()
     */
    close() {
        this.socket?.close()
    }
}
