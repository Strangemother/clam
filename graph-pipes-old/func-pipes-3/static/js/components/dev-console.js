window.devConsoleComponent = {
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
}