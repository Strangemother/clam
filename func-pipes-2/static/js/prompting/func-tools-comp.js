
const FunctionCall = {
  props: ['uuid', 'panel']
  , emits: ['updatePost']
  , template: document.querySelector('.templates .panel-template .function-call').innerHTML
  , methods: {

        addInboundPip(panel) {
            panel.pipsInbound.push({
              name: Math.random().toString(32).slice(3)
            })
        }

        , addOutboundPip(panel) {
            panel.pipsOutbound.push({
              name: Math.random().toString(32).slice(3)
            })
        }

        , pipClick($event, panel, pip, i) {
            console.log(event, panel)
            window.dispatchEvent(new CustomEvent('pipclick', {
                detail: {
                    panel
                    , pip
                    , i
                }
            }))
        }

  }
}

nodeRegister.FunctionCall = FunctionCall


const TextInput = {
  props: ['uuid', 'panel']
  , template: document.querySelector('.templates .panel-template .text-input').innerHTML
  , methods: {

        addInboundPip(panel) {
            panel.pipsInbound.push({
              name: Math.random().toString(32).slice(3)
            })
        }

        , addOutboundPip(panel) {
            panel.pipsOutbound.push({
              name: Math.random().toString(32).slice(3)
            })
        }

        , pipClick($event, panel, pip, i) {
            console.log(event, panel)
            window.dispatchEvent(new CustomEvent('pipclick', {
                detail: {
                    panel
                    , pip
                    , i
                }
            }))
        }

  }
}

nodeRegister.TextInput = TextInput