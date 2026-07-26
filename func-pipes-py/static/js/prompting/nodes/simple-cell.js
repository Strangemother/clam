

const SimpleCell = {
    props: ['uuid', 'panel']
    , template: getTemplateHTML('.simple-cell')
    , mounted() {

        this.panel._viewComponent = this
    }
    , unmounted() {
        if(this.panel._viewComponent === this) {
            this.panel._viewComponent = null
        }
    }

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
            return data + 1
        }
    })
}

nodeRegister.SimpleCell = SimpleCell