const CLOSE_THINKING = '</think>'
const OPEN_THINKING = '<think>'

const MessageListApp = {

    data() {
        return {

            /* The single "live message" is always on the view.
            populated by these bound values.
            */
            liveValue: 'no message'
            , liveResponse: 'no response'
            , liveMessageStash: ''
            , previousLiveValue: ''
            , liveMessage: {
                text: "live message user text"
                , response: "live message response text"
                , metaKey: -1
                , origin_id: -1
                , streaming: false
                , model_name: 'no model'
                , historyCount: 0
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
            // this.liveMessage.historyCount += 1
            // this.liveValue = e.detail.message
        }

        , resendUserText(){

            this.liveMessage.historyCount += 1
            let copyMessage = JSON.parse(JSON.stringify(
                                Object.assign({},
                                    this.liveMessage,
                                    {histories: undefined}
                                )
                            ))
            let histories = this.liveMessage.histories
            if(histories == undefined) {
                histories = []
            };

            histories.push(copyMessage)
            this.liveMessage.histories = histories

            UserMessage.emit({
                message: this.liveMessage.text
                /* Apply a meta key, to track the responses and
                pop them into the live message. */
                , _meta: Math.random().toString(32)
                // , from: ev
            })
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
                        this.dynamicResponseStreamStart(e.detail)
                    }
                }

                if(data.code == 1516) {
                    /* Stream close */
                    if(this.liveMessage.origin_id == data.origin_id) {
                        /* This origin has stopped stream.*/
                        this.liveMessage.streaming = false
                        this.liveMessageStash = ''
                        this.previousLiveValue = ''
                    }
                }

                if(data.code == 1519) {
                    /* stream info. */
                    console.log('stream info said', data)
                    console.log(data.result.model_name)
                    if(this.liveMessage.origin_id == data.origin_id) {
                        console.log('Setting current model name')
                        this.$refs.modelName.textContent = data.result.model_name
                        // this.liveMessage.model_name = data.model
                    }

                    if(!data.raw) {
                        // nothing to process...
                        return
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
                        this.dynamicResponseClose(e.detail)

                    }
                }


                if(this.liveMessage.origin_id == data.origin_id
                    && this.liveMessage.streaming == true) {
                    // This message is for this unit, and
                    // is in streaming mode.
                    this.dynamicResponseInsert(e.detail)
                    let peformRaw = false;
                    if(peformRaw) {

                        let value = data.raw
                        if(value == OPEN_THINKING || value == CLOSE_THINKING) {
                            // Is a special.
                            // this.liveMessage.response += `<hr>`
                            this.liveMessageStash += this.previousLiveValue + `<hr>`
                            this.previousLiveValue = ''
                        } else {
                            /* Instead of span everything, we span the _last token_
                            */
                            this.liveMessageStash += this.previousLiveValue
                            this.liveMessage.response = this.liveMessageStash
                            this.previousLiveValue = value

                            let $el = document.querySelector('#message_list')
                            $el.scrollTop = $el.scrollHeight;

                        }
                    }

                }

            }
        }

        , dynamicResponseStreamStart(detail) {
            /*A new stream to start */
            // copy into history stack.
            let outputArea = this.$refs.dynamicResponse;
            outputArea.innerHTML = ''
            outputArea.outputCell = undefined
        }

        , dynamicResponseClose(detail) {
            // copy the output cell into the history

        }

        , dynamicResponseInsert(detail) {

            let data = detail.data
            let outputArea = this.$refs.dynamicResponse;

            let outputCell = outputArea.outputCell

            if(outputCell == undefined) {
                /* Create a new one.*/
                outputCell = document.createElement('span')
                outputCell.classList.add('outputCell')
                outputCell.id = Math.random().toString(32)
                // Start of the output text.
                outputCell.textContent = ''

                outputArea.outputCell = outputCell
                outputArea.appendChild(outputCell)
            }

            let raw = data.raw
            if(raw == OPEN_THINKING || raw == CLOSE_THINKING) {
                /* Shoudl create a new cell and write it into the cireview.*/

                if(raw == OPEN_THINKING){
                    console.log('Open thinking', raw)

                    let thinkingCell = document.createElement('span')
                    thinkingCell.classList.add('thinkingCell')
                    thinkingCell.id = Math.random().toString(32)
                    // Any prefix text here.
                    thinkingCell.appendChild(thinkingTag(raw))

                    thinkingCell.originOutputCell = outputArea.outputCell

                    outputCell.appendChild(thinkingCell)
                    outputArea.outputCell = thinkingCell
                } else if(raw == CLOSE_THINKING){
                    /* Finish the cell. backout to the original.*/
                    console.log('close thinking', raw)
                    outputArea.outputCell.appendChild(thinkingTag(raw))
                    // outputArea.outputCell.innerHTML += thinkingTag(raw)
                    let renderCell = document.createElement('span')
                    renderCell.classList.add('renderCell')

                    outputArea.outputCell.originOutputCell.appendChild(renderCell)
                    outputArea.outputCell = renderCell

                }
            } else{
                outputCell.innerHTML += raw
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

const thinkingTag = function(value){
    let node = document.createElement('span')
    node.classList.add('thinking-tag')
    node.id = Math.random().toString(32)
    // Any prefix text here.
    node.innerHTML = escapeHtml(value)
    return node
}

function escapeHtml(str) {
  return str.replace(/[&<>"'/]/g, function (char) {
    return ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
      '/': '&#47;',
    })[char];
  });
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
