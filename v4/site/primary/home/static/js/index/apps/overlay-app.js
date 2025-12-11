/* The panel for first entry; containing a _go_ button (amongst other buttons). */
const OverlayPanelsApp = {
    mounted() {
    }

    , methods: {
        gotoPrimary(e) {
            console.log('gotoPrimary', e)
            let owner = document.querySelector('.alpha-grid-container')
            owner.dataset.stage = 2
            SetFirstFocusEvent.emit()
        }
    }

}

const overlayPanelsApp = Vue.createApp(OverlayPanelsApp).mount('#overlay')

