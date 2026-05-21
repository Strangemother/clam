/*
  prompting/index.js  (app shell)
  ────────────────────────────────
  Thin entry point — bootstraps the Vue app and composes all method groups.

  Load order in prompting.html:
    nodes.js → prompt-spawn.js → prompt-signal.js → prompt-llm.js →
      prompt-wiring.js → prompt-persist.js → prompt-transform.js →
      prompt-pyfunc.js → prompt-event.js → index.js
*/

const { createApp, nextTick } = Vue

dragHost = new DragSolo()


// camelCase in JavaScript
const FunctionCall = {
  props: ['postTitle', 'panel'],
  emits: ['updatePost'],
  template: document.querySelector('.templates .panel-template').innerHTML
}


const app = createApp({

    data() {
        return {
            panels: [],
            available: [],
            selected: ''
        }
    },

    async mounted() {
        // Models must be fetched manually via the toolbar after setting the endpoint.
        // Prompting uses transform-based zoom so node contents scale without reflow.
        window.infiniteDrag = new ZoomableInfiniteDrag('.layer-space', '.panel', {
            zoomMode: 'transform',
        });

        this.spawnPanel()

        fetch('/nodes/')
            .then((d)=>d.json())
            .then(
                (names)=>{
                    this.available = names
                }
            )
    },

    methods: {
        spawnButton(){
            this.spawnPanel()
        }

        , spawnPanel(){
            console.log('spawnPanel', this.selected)
            let funcName = this.selected

            let d = {
                pipsInbound: [ 'one', 'two', 'three' ]
                , pipsOutbound: [ 'four', 'five']
                , type: 'function-call'
                , funcName
                , id: Math.random().toString(32).slice(3)
            }

            this.panels.push(d)
            nextTick(() => {
                const el = this.$refs[`panel-${d.id}`][0]
                stickAll(el)
                dragHost.enable(el)
            })
        }
    },

});

app.component('FunctionCall', FunctionCall)
app.mount('#app')
