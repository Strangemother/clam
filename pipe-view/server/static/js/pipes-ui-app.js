/*

*/

const spawnWindow = function(conf={}) {
    /* Generally called by the UI button or can be called manually.
    Create a new winbox window and bind the new interals with a
    Vue app.

    Returns the created winbox window, find the app within `result.vueApp`

    */

    let confName = conf.name;
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
        , onfocus(){
            console.log('Focus', confName)
            dispatchFocusNodeEvent({ name: confName})
        }
        ,  onmove: function(x, y){
            // console.log('Moved to', x, y)
            dispatchRequestDrawEvent()
        }

    };
    Object.assign(winapp, conf);
    let _window = new WinBox(confName, winapp);

    // pipes.winbox-app.js
    createWinboxVueApp(_window, conf)
    return _window
}


const createUIApp = function(mountSelector='#mini_app') {
    /*
        This Vue app maintains the ui clickable buttons
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
        newPanelName: "label"
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

        , onFocusNode(event) {
            console.log('onFocusNode', event.detail)
            this.focusNode = event.detail
        }

        , redrawCanvas(){
            pipesTool.draw();
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

        , stepOnceHighlighted(){

            let start = false;

            if(this._stepHighlightEntry == undefined) {
                // start
                // console.log('stepOnceHighlighted start', this.focusNode)
                start = true
            } else {

                if(this._stepHighlightEntry.name != this.focusNode.name) {
                    console.log('Node change.')
                    pipesTool.lights.clearCycle()
                    start = true
                }
            }

            if(start == true) {
                pipesTool.lights.cycleFrom(this.focusNode.name)
                this._stepHighlightEntry = this.focusNode
            }

            // console.log('stepOnceHighlighted continue', this.focusNode)
            pipesTool.lights.stepLights()
        }

        , startStepHighlighted(startNode=this.focusNode) {

            if(startNode == undefined) {
                startNode = this._stepHighlightEntry
            }

            if(this._stepHighlightEntry != undefined) {
                this.stopStepHighlighted()
            }

            console.log('start from', startNode)
            this._stepHighlightEntry = startNode

            pipesTool.lights.runLights(startNode.name)

        }

        , stopStepHighlighted() {
            console.log('Stopping highlighter', this._stepHighlightEntry)
            pipesTool.lights.stopLights()
            this._stepHighlightEntry = undefined
        }

        , spawnWindow(conf={name: this.newPanelName}) {

            let r = this.windowMap[conf.name] = spawnWindow(conf)
            return r
        }

        , getTip(label, direction, index=0) {
            let windowApp = this.windowMap[label]
            let unit = windowApp.vueApp.getTip(direction, index)
            return unit
        }

        , startExecuteLoop(startNode=this.focusNode) {
            if(this._walkerExecution != undefined) {
                this.stopExecuteLoop()
            }

            this._walkerExecution = pipesTool.walker.executeLoop(startNode.name, 2)
        }

        , stopExecuteLoop(){
            if(this._walkerExecution == undefined) {
                console.log('No executor to stop.')
                return false;
            }

            this._walkerExecution.stop()
            this._walkerExecution = undefined;
            return true
        }
    }

    const res = PetiteVue.createApp(app)
    listenEvent('focusnode', app.onFocusNode.bind(app))
    res.mount(mountSelector)
    return app
};
