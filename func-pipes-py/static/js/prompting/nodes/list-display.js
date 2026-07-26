
const ListDisplay = Object.assign({}, NodeBase, {
    // props: ['uuid', 'panel']
    template: getTemplateHTML('.list-display')
    , data() {
        return {
            items: [
                { pip: 'in', value: 'one'},
                { pip: 'out', value: 'two'},
                { pip: 'out', value: 'another'},
                { pip: 'in', value: 'thank you'}
            ]
        }
    }
    , methods: Object.assign({}, PanelBaseMethods, {
        sendContent() {
            console.log('sendContent', this.userText)
            this.saveSend(this.userText)
        }

        , saveSend(text, inputPip='out') {
            this.items.push({ pip: inputPip, value: text })

            simpleBridge.emitResultThrough(text, {
                id: this.panel.id,
                pip: inputPip // currently ignored
            })
        }

        , customCallback(data, pip) {
            // somehow called be the spawnpanel callback.
            console.log('customCallback', data, pip)
            this.saveSend(data, pip)
            return data

        }
    })
});

nodeRegister.ListDisplay = ListDisplay
