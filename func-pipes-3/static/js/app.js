var INIT_NODES = [
    {
        label: 'A',
        title: 'Node A',
        description: 'This is node A',
        x: 0,
        y: 0,
    }
]

const app = Vue.createApp({
    data() {
        return {
            title: 'Func Pipes 3',
            message: 'Python graph workspace',
            nodes: INIT_NODES,
            backendSocket: null,
        }
    },

    mounted() {
        this.backendSocket = new BackendSocket()
        window.backendSocket = this.backendSocket
        this.backendSocket.onMessage(this.handleBackendCommand.bind(this))
    },

    methods: {
        handleBackendCommand(command) {
            // Backend command handling will be added here.
            console.log('Received command from backend:', command)
        },
    },
})

app.component('socket-control', {
    props: {
        socket: { type: Object, default: null },
    },
    data() {
        return {
            url: this.socket?.url || '',
            status: 'disconnected',
        }
    },
    watch: {
        socket: {
            immediate: true,
            handler(socket) {
                if (!socket) return
                this.url = socket.url
                socket.onStatus = (status) => { this.status = status }
            },
        },
    },
    methods: {
        toggleConnection() {
            if (!this.socket) return
            if (this.status === 'connected' || this.status === 'connecting') {
                this.socket.close()
            } else {
                this.socket.connect(this.url)
            }
        },
    },
    template: document.querySelector('.socket-control-template').innerHTML,
})

app.component('dev-console', {
    props: {
        socket: { type: Object, default: null },
    },
    data() {
        return {
            message: '{"kind":"command","name":"demo.ping"}',
            messages: [],
        }
    },
    watch: {
        socket: {
            immediate: true,
            handler(socket) {
                if (socket) socket.onMessage(this.captureMessage.bind(this))
            },
        },
    },
    methods: {
        captureMessage(message) {
            this.messages.push({ direction: 'in', message })
        },
        sendMessage() {
            if (!this.socket) return
            let message = this.message
            try {
                message = JSON.parse(this.message)
            } catch {
                // Plain text is valid relay traffic.
            }
            try {
                this.socket.send(message)
                this.messages.push({ direction: 'out', message })
            } catch (error) {
                this.messages.push({ direction: 'error', message: error.message })
            }
        },
        formatMessage(message) {
            return typeof message === 'string'
                ? message
                : JSON.stringify(message, null, 2)
        },
    },
    template: document.querySelector('.dev-console-template').innerHTML,
})

app.component('surface-panel', {
    props: {
        panelClass: { type: String, default: '' },
        label: { type: String, required: true },
        title: { type: String, required: true },
        description: { type: String, required: true },
        x: { type: Number, default: 0 },
        y: { type: Number, default: 0 },
    },
    template: document.querySelector('.surface-panel-template').innerHTML,
})

const mountedApp = app.mount('#app')
