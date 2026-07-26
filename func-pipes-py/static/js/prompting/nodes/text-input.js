
const TextInput = Object.assign({}, NodeBase, {
    // props: ['uuid', 'panel']
    template: getTemplateHTML('.text-input')
    , methods: Object.assign({}, PanelBaseMethods, {
        sendContent() {
            console.log('sendContent', this.userText)

            simpleBridge.emitResultThrough(this.userText, {
                id: this.panel.id,
                pip: 'out' // currently ignored
            })
        }

        , customCallback(data, pip) {
            // somehow called be the spawnpanel callback.
            console.log('customCallback', data, pip)
            // this.panel.viewData.value = data
            this.userText = data
            return data
        }
    })
});

nodeRegister.TextInput = TextInput
