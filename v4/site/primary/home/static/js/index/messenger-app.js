/*
This file manages the binding between the input field (user messages)
and the live socket.

It is loaded when ready to collect the global socket, using methods from
the websocket-tools

*/

const messageCallbacks = {}
const sessionCache = {}


const messengerMain = function() {
    RequestSocketConnectEvent.listen(function(e){
        let url = cache.globalSocketEndpoint
        return getSocket(url)
    });

    /* Listen to events from a websocket downpipe,
    built into a websocket wrapper  (connectsocket) */
    GlobalSocketEvent.listen((e)=>{
        /* { type: 'open'} */
        let data = e.detail.data
        let _meta = data?._meta

        let origin_id = data?.origin_id
        let dataWithCB = undefined;

        if(messageCallbacks[_meta] != undefined) {
            dataWithCB = messageCallbacks[_meta];
        } else if(messageCallbacks[origin_id] != undefined) {
            dataWithCB = messageCallbacks[origin_id];
        }

        if(data?.code == 1200) {
            console.log('RECV WAKE')
            sessionCache.session_id = data.session_id
        }

        if(dataWithCB != undefined) {

            if(data.code == 1111) {
                /* Is acceptance. */
                console.log(' -- register callback receipt')
                dataWithCB['receipt'] = data
                dataWithCB['origin_id'] = origin_id
                messageCallbacks[origin_id] = dataWithCB
            } else {
                dataWithCB.callback(e)
                let _meta2 = _meta == undefined? dataWithCB._meta: _meta

                if(_meta2){
                    delete messageCallbacks[_meta2]
                }

                if(origin_id) {
                    delete messageCallbacks[origin_id]
                }
            }
        }
    })

    UserMessage.listen((e)=>{
        let text = e.detail.message
        console.log('messenger-app received userMessage', text)
        let _meta = e.detail._meta
        if(_meta == undefined){
            _meta = Math.random().toString(32)
        }


        let session_id = e.detail.session_id
        if(session_id == undefined){
            session_id = sessionCache.session_id
        }

        /* in websocket-tools */
        sendJSONMessage({text, _meta, session_id })
    })

    SystemMessage.listen((e)=> {
        let data = e.detail
        let _meta = data._meta
        if(_meta == undefined){
            _meta = Math.random().toString(32)
        }

        if(data.callback) {
            messageCallbacks[_meta] = data
        }

        let session_id = data .session_id
        if(session_id == undefined){
            data.session_id = sessionCache.session_id
        }

        /* in websocket-tools */
        sendJSONMessage(data)
    })


}


window.addEventListener('DOMContentLoaded', ()=>{
    console.log('messenger app DOMContentLoaded')
    messengerMain()
})