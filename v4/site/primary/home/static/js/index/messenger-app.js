/*
This file manages the binding between the input field (user messages)
and the live socket.

It is loaded when ready to collect the global socket, using methods from
the websocket-tools

 */
const messengerMain = function() {
    RequestSocketConnectEvent.listen(function(e){
        let url = cache.globalSocketEndpoint
        return getSocket(url)
    });

    UserMessage.listen((e)=>{
        let text = e.detail.message
        console.log('messenger-app received userMessage', text)
        sendJSONMessage({text, _meta: Math.random().toString(32)})
    })
}


window.addEventListener('DOMContentLoaded', ()=>{
    console.log('messenger app DOMContentLoaded')
    messengerMain()
})