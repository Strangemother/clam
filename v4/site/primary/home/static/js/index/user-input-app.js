
const InputSpaceApp = {
    mounted() {
        console.log('Input Mounted')
        UserMessage.listen(this.exampleEventHandler.bind(this))
        SetFirstFocusEvent.listen((e)=>{
            setTimeout(()=>{
                this.messageField().focus()
            }, 50)
        })

        let isEmpty = this.userText(true).length == 0

        this.showPlaceholder(!isEmpty)

    }

    , methods: {
        exampleEventHandler(e) {
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

            console.log('Accepted Printable: code', code, 'char', char)
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
                , from: ev
            })
        }
    }

}

const inputSpaceApp = Vue.createApp(InputSpaceApp).mount('#input_space')

