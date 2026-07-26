
const PanelBaseMethods = {

    addInboundPip(panel) {
        panel.pipsInbound.push({
            name: Math.random().toString(32).slice(3),
            execute: false
        })
    }

    , addOutboundPip(panel) {
        panel.pipsOutbound.push({
          name: Math.random().toString(32).slice(3)
        })
    }

    , pipClick($event, panel, pip, i) {
        console.log(event, panel)
        // window.dispatchEvent(new CustomEvent('pipclick', {
        //     detail: {
        //         panel
        //         , pip
        //         , i
        //     }
        // }))
        dispatchEvent('pipclick', {
                panel
                , pip
                , i
            })
    }

}


const NodeBase = {
    props: ['uuid', 'panel']
    , emits: ['updatePost']
    , data() {
        return {}
    }

    // , template: getTemplateHTML('.function-call')
    , mounted() {
        this.panel._viewComponent = this
    }

    , unmounted() {
        if(this.panel._viewComponent === this) {
            this.panel._viewComponent = null
        }
    }

}