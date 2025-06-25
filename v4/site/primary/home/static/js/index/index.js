/*
The "primary" file to initiate the interface.

This contains the users UI "cache" and can be edited by UI components.
 */
const uuid = Math.random().toString(32).slice(2)

const cache = {
    primarySocket: undefined
    , socketConnected: false
    , used: false
    , globalSocketEndpoint: 'ws://localhost:8765'
}


const indexMain = function() {
    RequestSocketConnectEvent.emit({})
}


window.addEventListener('DOMContentLoaded', ()=>{
    console.log('index DOMContentLoaded')
    indexMain()
})