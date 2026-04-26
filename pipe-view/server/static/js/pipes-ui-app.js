/*

*/

const createUIApp = function(mountSelector='#mini_app') {
    /*
        This app maintains the ui clickable buttons
        and the windows made by winbox.

        exposed as `app`.
     */
    let app = {
        // cacheCopy: reactive(cache)
        // , messages: reactive([])
        // , partialState: reactive({
        //     status: "waiting"
        //     , counter: 0
        // })
        newPanelName: "Strange Apple"
        , animateLines: false

        , windowMap: {}

        , saveButton() {
            // save the view to localstore.
            pipesTool.save()
        }

        , restoreButton() {
            // restore the view from localstore.
            pipesTool.restore()
        }

        , animateLinesCheckChange(event) {
            let checked = event.target.checked
            if(checked) {
                if(this._animating) {
                    console.log('Already animating', this._animating)
                }
                this._animating = pipesTool.animDraw()
            } else {
                    console.log('Stopping anim', this._animating)
                    pipesTool.layerGroup.stopAnimDraw()
                    this._animating = null
            }
        }

        , spawnWindow(conf={name: this.newPanelName}) {
            let name = conf.name;
            let winapp = {
                class: [
                    "no-min"
                    , "no-max"
                    , "no-full"
                    // , "no-resize"
                    // , "no-move"
                    ]
                , x: "center"
                , y: "center"
                , width: "20%"
                , height: "20%"
                , mount: document
                            .getElementById("window_content")
                            .cloneNode(true)
                , root: document.querySelector("main")

                ,  onclose: function(force){
                    console.log('Unmount app')
                    // this.vueApp.unmount()
                    return force;
                    // return !confirm("Close window?");
                }
                ,  onmove: function(x, y){
                    // console.log('Moved to', x, y)
                    dispatchRequestDrawEvent()
                }

            };
            Object.assign(winapp, conf);
            let _window = new WinBox(name, winapp);

            createWindowApp(_window, conf)
            this.windowMap[name] = _window
            return _window
        }

        , getTip(label, direction, index=0) {
            let windowApp = this.windowMap[label]
            let unit = windowApp.vueApp.getTip(direction, index)
            return unit
        }
    }

    const res = PetiteVue.createApp(app)
    res.mount(mountSelector)
    return app
};
