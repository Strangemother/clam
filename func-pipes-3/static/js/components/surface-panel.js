window.surfacePanelComponent = {
    props: {
        panelClass: { type: String, default: '' },
        label: { type: String, required: true },
        title: { type: String, required: true },
        description: { type: String, required: true },
        x: { type: Number, default: 0 },
        y: { type: Number, default: 0 },
    },
    template: document.querySelector('.surface-panel-template').innerHTML,
}