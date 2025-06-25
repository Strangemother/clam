/*
    The app at the footer of the page, currently dedicated to socket information
*/
const SocketStatusApp = {

    data() {
        return {
            socketEndpoint: cache.globalSocketEndpoint //"//socket.unresearch.ai"
            , statusMessage: 'no status'
        }
    }

    , mounted() {
        UserMessage.listen(this.userMessage.bind(this))
        GlobalSocketEvent.listen(this.globalSocketEventHandler.bind(this))
    }

    , methods: {
        userMessage(e) {
            console.log('socket-status heard user message')
            // this.liveValue = e.detail.message
        }
        , globalSocketEventHandler(d) {
            /*{ type: 'open'}*/

            this.statusMessage = d.detail.type
        }

        , addressClick(e) {
            // if not connected, attempt connect.
            console.log('address click. Connected:', cache.socketConnected)
            if(!cache.socketConnected) {
                this.statusMessage = 'requested'
                RequestSocketConnectEvent.emit({})
            }
        }
    }
}

const socketStatusApp = Vue.createApp(SocketStatusApp)
let mountedSocketStatusApp = socketStatusApp.mount('#status_bar')
