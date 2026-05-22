

const TextInput = {
  props: ['uuid', 'panel']
  , template: getTemplateHTML('.text-input')
  , methods: {

        addInboundPip(panel) {
            panel.pipsInbound.push({
              name: Math.random().toString(32).slice(3)
            })
        }

        , sendContent() {
          console.log('sendContent')
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