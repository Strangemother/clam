/*

USer typy typy space. A Vue app to listen for events and activate posts.

 */
const InputSpaceApp = {
    mounted() {
        console.log('Input Mounted')

        /* User sends a message. We _listen_ for the user message event,
        rather than the internal keydown, to capture potential view delays. */
        UserMessage.listen(this.exampleEventHandler.bind(this))

        /* The  SetFirstFocusEvent.emit() is dispatched by the message list app,
        when the view _asks_ for the correct view.

        Focus on the message field.
        */
        SetFirstFocusEvent.listen((e)=>{
            setTimeout(()=>{
                this.messageField().focus()
            }, 50)
        })

        /* Hide the placeholder if there is pre-prepared text. */
        let isEmpty = this.userText(true).length == 0
        this.showPlaceholder(!isEmpty)

    }

    , methods: {

        exampleEventHandler(e) {
            /* The user message event, dispatched by the system
            when the user sends a message through sendUserText

            We assume this message was due to inputs from the message field. */
            console.log('self acknowledging message', e)
            this.messageField().textContent = "";
        }

        , keydownHandler(ev) {
            // console.log('keydown')
            const isEmpty = ev.target.textContent.length == 0
            if(isEmpty) {
                /* if empty, assume the next char will populate.
                Therefore perform this early.

                It makes removal if the input field text
                (_from empty_ to populated) a bit snappier. */
                // TODO: change only when the next char is a visible char.
                if(this.isPrintable(ev)) {
                    this.showPlaceholder(true)
                }
            }
        }

        , keyupHandler(ev) {
            // console.log('keyup', ev)
            const isEmpty = ev.target.textContent.length == 0

            this.showPlaceholder(!isEmpty)
        }

        , enterupHandler(ev) {
            // console.log('enterup')
            if(ev.ctrlKey) {
                // this.getPlaceholder().textContent = 'Message Recieved'
                // eventCenter.dispatch(ev)
                this.sendUserText(ev)
            }
        }

        , sendButton(ev) {
            this.sendUserText({
                target: this.messageField()
            })
        }

        , enterdownHandler(ev) {
            // console.log('enterdown')
        }

        , userText(cleaned=false) {
            let r = this.messageField().textContent
            return cleaned? r.trim(): r;
        }

        , messageField() {
            return this.$refs.user_message
        }

        , isPrintable(ev) {
            const code = ev.keyCode
            const char = ev.charCode
            const codes = [
                13 // enter
                , 8 // backspace
                , 9 // tab
                , 16 // shift
                , 18 // alt
                , 17 // ctrl
                , 19 // pause break
                , 33, 34 // Pgup/down
                , 35// end
                , 36 // home
                , 37, 38, 39, 40 // arrows
                , 45, 46 // ins, del
                , 93 // mouse menu
                , 144 // numlock
                , 145 // scrlock
            ]

            if(codes.indexOf(code) > -1) {
                return false
            }

            // console.log('Accepted Printable: code', code, 'char', char)
            return true
        }

        , showPlaceholder(show=true) {
            let name = 'add'
            if(show === false) {
                name = 'remove'
            }
            this.getPlaceholder().classList[name]('hide')
        }

        , getPlaceholder() {
            return this.$refs.placeholder
        }

        , sendUserText(ev){
            let target = ev.target
            console.log('dispatch', ev)
            UserMessage.emit({
                message: target.textContent
                /* Apply a meta key, to track the responses and
                pop them into the live message. */
                , _meta: Math.random().toString(32)
                , from: ev
            })
        }

        , getModels(ev) {
            console.log('getModels')
            this.getSystemAction({action: 'get_models'}, (e)=> {
                    console.log('get_models callback')
                    console.log(e.detail)
                    console.log(e)
            })
        }
        , setModel(ev) {
            console.log('setModel')
            this.getSystemAction(
                    {action: 'set_model', model_name: 'deepseek-r1:latest'}, (e)=> {
                    console.log('set_models callback')
                    console.log(e.detail)
            })
        }

        , getSystemAction(action, callback) {
            console.log('getModels')
            SystemMessage.emit(Object.assign(action, {
                routing: 'command'
                /* Apply a meta key, to track the responses and
                pop them into the live message. */
                , _meta: Math.random().toString(32)
                // , from: ev
                , callback
            }))
        }

        , getRoleSystem(action, callback) {

            SystemMessage.emit({
                action: 'set_role'
                , routing: 'command'
                , first_message: {
                    role: "system"
                    , content: "You are an angry short-tempered anti-assistant. Every query is met with disdain, and rudeness. Be rude, arrogant, terse. Every response must contain a swear word."
                }
                /* Apply a meta key, to track the responses and
                pop them into the live message. */
                , _meta: Math.random().toString(32)
                // , from: ev
                , callback
            })
        }

        , getRole(ev) {
            this.getSystemAction({action: 'get_role'}, (e)=> {
                    console.log('get_role callback')
                    console.log(e.detail)
                    console.log(e)
            })
        }
    }

}

const inputSpaceApp = Vue.createApp(InputSpaceApp).mount('#input_space')

