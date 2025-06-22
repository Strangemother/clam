
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

