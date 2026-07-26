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