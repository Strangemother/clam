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

const mountedApp = app.mount('#app')
