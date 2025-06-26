
const MessageListApp = {

    data() {
        return {

            /* The single "live message" is always on the view.
            populated by these bound values.
            */
            liveValue: 'no message'
            , liveResponse: 'no response'
            , liveMessage: {
                text: "live message user text"
                , response: "live message response text"
                , metaKey: -1
                , origin_id: -1
                , streaming: false
                , model_name: 'no model'

            }

            /* Existing messages in the view. Usually blank*/
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
        GlobalSocketEvent.listen(this.globalSocketEventHandler.bind(this))

    }

    , methods: {
        userMessage(e) {
            /* The user has dispatched a message (likely from
            the user-input-app::sendJSONText)

            Capture the upstream data and populate the live message

            This contains meta data to catch the incoming messages. */
            let detail = e.detail
            let _meta = detail._meta
            console.log('message list heard user message', detail)
            this.liveMessage.text = detail.message
            this.liveMessage.metaKey = _meta
            // this.liveValue = e.detail.message
        }

        , globalSocketEventHandler(e){
            // { type: 'message', data }
            let detail = e.detail;
            if(detail.type == 'message') {
                let data = detail.data

                if(data.code == 1111) {
                    if(data._meta == this.liveMessage.metaKey) {
                        /* Is accept */
                        this.liveMessage.confirmed = true
                        this.liveMessage.origin_id = data.origin_id
                    }
                }

                if(data.code == 1515) {
                    if(this.liveMessage.origin_id == data.meta.origin_id) {
                        /* This origin is about to stream.*/
                        this.liveMessage.streaming = true
                        this.liveMessage.response = ''
                    }
                }

                if(data.code == 1516) {
                    if(this.liveMessage.origin_id == data.origin_id) {
                        /* This origin has stopped stream.*/
                        this.liveMessage.streaming = false
                    }
                }

                if(data.code == 1517) {
                    /* A complete version of the raw stream.
                        **response_token/s**: This measures the average number of tokens
                                              (words or subwords, e.g., "wordpiece")
                                              generated per second by the model
                                              as a response to input prompts.


                        **prompt_token/s**: Similar to above, but for the input
                                            prompt itself. This is the average
                                            number of tokens in each prompt
                                            received by the model.

                        **total_duration**: The total time taken by the model to
                                            process all prompts and generate
                                            responses. e.g 13.64 seconds (13633.84 milliseconds).

                        **load_duration**: This measures the time taken for
                                           the model to load or initialize
                                           itself before processing the first prompt.
                                           e.g. short duration of
                                           about 3.59 seconds (3593 milliseconds)

                        **prompt_eval_count**: The number of prompts that were
                                         actually evaluated by the model,
                                         rather than skipped or ignored.


                        **prompt_eval_duration**: The total time taken for the
                                            model to evaluate all these prompts.
                                            e.g 2.62 seconds (2620.7 milliseconds).

                        **eval_count**: Similar to prompt_eval_count,
                                        but for a different evaluation metric or
                                        phase.

                        **eval_duration**: The time taken for this particular
                                           evaluation phase.
                    */
                    if(this.liveMessage.origin_id == data.origin_id) {
                        let d = data.result
                        this.liveMessage.final = d
                        this.liveMessage.model_name = d.model
                    }
                }

                if(this.liveMessage.origin_id == data.origin_id
                    && this.liveMessage.streaming == true) {
                    // This message is for this unit, and
                    // is in streaming mode.
                    this.liveMessage.response += `<span>${data.raw}</span>`
                }

            }
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
