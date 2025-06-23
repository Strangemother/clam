/*
    The app at the footer of the page, currently dedicated to socket information
*/
const SocketStatusApp = {

    data() {
        return {}
    }

    , mounted() {
        UserMessage.listen(this.userMessage.bind(this))
    }

    , methods: {
        userMessage(e) {
            console.log('socket-status heard user message')
            // this.liveValue = e.detail.message
        }
    }
}

const socketStatusApp = Vue.createApp(SocketStatusApp)
let mountedSocketStatusApp = socketStatusApp.mount('#status_bar')
