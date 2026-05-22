(function() {
    const getPanelSelector = function(label) {
        const value = String(label)
            .replace(/\\/g, '\\\\')
            .replace(/"/g, '\\"')

        return `[data-panel-id="${value}"]`
    }

    const getPipNode = function(label, direction, index) {
        const panel = document.querySelector(getPanelSelector(label))
        if(!panel) {
            return null
        }

        const pipSelector = direction == 'outbound'
            ? '.pips.outbound .pip'
            : '.pips.inbound .pip'

        const pips = panel.querySelectorAll(pipSelector)
        return pips[index] || null
    }

    window.app = window.app || {}
    window.app.getTip = function(label, direction, index=0) {
        return {
            get node() {
                return getPipNode(label, direction, index)
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        if(typeof createPipesRuntime != 'function') {
            return
        }

        createPipesRuntime()

        if(window.clItems && typeof window.clItems.animDraw == 'function') {
            window.clItems.animDraw()
        }

        const requestDraw = function() {
            if(typeof dispatchRequestDrawEvent == 'function') {
                dispatchRequestDrawEvent()
            }
        }

        document.addEventListener('dragmove', requestDraw)
        document.addEventListener('panspace', requestDraw)
        document.addEventListener('zoomspace', requestDraw)
    })
})()