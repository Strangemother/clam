
const MessageListApp = {

    data() {
        return {
            liveValue: 'no message'
            , liveResponse: 'no response'
            , liveMessage: {
                text: "live message user text"
                , response: "live message response text"
            }
            , messages: [
                {
                    type: 'system-message'
                    , text: "Unique system message. Start here."
                }
                , {
                    type: 'pair-message'
                    , text: "A message from the user"
                    , response: 'A Response from the service'
                }
            ]
        }
    }

    , mounted() {
        UserMessage.listen(this.userMessage.bind(this))
    }

    , methods: {
        userMessage(e) {
            console.log('message list heard user message')
            this.liveMessage.text = e.detail.message
            // this.liveValue = e.detail.message
        }

        , gotoPrimary(e) {
            console.log('gotoPrimary', e)
            let owner = document.querySelector('.alpha-grid-container')
            owner.dataset.stage = 2
            SetFirstFocusEvent.emit()
        }
    }

}

const PairMessageComponent = {
    props: ['message']
    , template: document.querySelector('.templates .user-message')
    , data() {
        return {
            userText: 'default user text'
            , responseText: 'default responseText'
        }
    }
    // , mounted() {
    //     console.log('pairMessageComponent mounted', this.message)
    // }
}


const SystemMessageComponent = {
    props: ['message']
    , template:document.querySelector('.templates .system-message')
    , data() {
        return {
            messageValue: 'messageValue'
        }
    }
}


const messageListApp = Vue.createApp(MessageListApp)
const pairMessageComponent = messageListApp.component('PairMessage', PairMessageComponent)
const systemMessageComponent = messageListApp.component('SystemMessage', SystemMessageComponent)

let mountedMessageListApp = messageListApp.mount('#message_list')
