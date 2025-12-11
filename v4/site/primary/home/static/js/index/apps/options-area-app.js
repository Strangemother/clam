/*
Buttons and extras next to the input space.

+ model selection
+ VAD Tool
...

 */
const OptionsAreaApp = {
    mounted() {
        console.log('OptionsArea')
    }

    , methods: {

         getModels(ev) {
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
                    {action: 'set_model', model_name: 'unsloth/gpt-oss-20b'}, (e)=> {
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

const optionsAreaApp = Vue.createApp(OptionsAreaApp).mount('#options_area')

