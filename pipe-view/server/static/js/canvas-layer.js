
/* Store incoming connection, for future storage */
const pipeData = {
    raw: []
    , connections: {}
}

class CanvasLayerGroup {
    // const clItems = new CanvasLayerGroup(cl1, cl2)
    constructor(...layers) {
        this.layers = layers
        document.addEventListener('connectnodes', this.connectNodesEvent.bind(this))
    }

    connectNodesEvent(event) {
        let obj = event.detail
        return this.connectNodes(obj)
    }

    connectNodes(obj) {
        console.log('connectNodes', obj)
        pipeData.raw.push(obj)



        // from / to
        let sd = obj.sender.direction // outbound
        let rd = obj.receiver.direction // inbound

        if(sd == rd) {
            console.error("same direction isn't possible.")
            return
        }

        let senderUnit = app.getTip(obj.sender.label, obj.sender.direction, obj.sender.pipIndex)
        let receiverUnit = app.getTip(obj.receiver.label, obj.receiver.direction, obj.receiver.pipIndex)

        let _id = `${obj.sender.label}-${obj.receiver.label}`

        console.log('Stashed', _id)
        pipeData.connections[_id] = {
            obj
            , senderUnit
            , receiverUnit
        }

    }

    draw(){
        this.renderConnections()
        requestAnimationFrame(this.renderFrame.bind(this));
    }

    renderFrame(delta){
        this.layers.forEach((layer)=>{
            layer.draw(delta)
        })
    }

    renderConnections(){
        for(let _id in pipeData.connections) {
            let conn = pipeData.connections[_id]

            let senderNode = conn.senderUnit.node
            let receiverNode = conn.receiverUnit.node

            let senderRect = senderNode.getBoundingClientRect()
            let receiverRect = receiverNode.getBoundingClientRect()

            console.log('From', conn.senderUnit, 'to', conn.receiverUnit)
            this.drawLine(_id, senderRect, receiverRect)
        }

    }

    drawLine(_id, senderRect, receiverRect) {
        console.log('From', senderRect, 'to', receiverRect)

        let tidyLine = {
            _id
            , a: senderRect
            , b: receiverRect
        }
        console.log('Installing line.')
        this.layers[1].addLine(tidyLine)
    }

}


class CanvasLayer {
    /* Manages lines on a canvas. */
    // const cl1 = new CanvasLayer('.canvas-container.back')
    constructor(selector) {
        this.selector = selector
        let _canvas = document.querySelector(selector)
        this.canvas = _canvas
        this.ctx = _canvas.getContext("2d");
        this.dimensions = this.stickCanvasSize(_canvas)
        this.renderFrame.bind(this)
        this.lines = []
    }

    draw(){
        requestAnimationFrame(this.renderFrame.bind(this));
    }

    clear(ctx=this.ctx, fillStyle=null) {
        /* Perform a standard 'clearRect' using the cached dimensions of the
        canvas.

            stage.clear(ctx)

        Synonymous to:

            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

        Apply an optional flood fillStyle:

            stage.clear(ctx, '#000')
        */
        let dimensions = this.dimensions
        ctx.clearRect(0, 0, dimensions.width, dimensions.height);

        if(fillStyle === null) { return }
        ctx.rect(0, 0, dimensions.width, dimensions.height);
        ctx.fillStyle = fillStyle
        ctx.fill();
    }

    addLine(tidyLine){
        this.lines[tidyLine._id] = tidyLine
    }

    renderFrame(delta){
        const ctx = this.ctx
        this.clear(ctx)
        console.log('renderFrame', delta)

        for(let k in this.lines) {
            let o =  this.lines[k]
            this.renderLine(o, ctx)
        }

        ctx.beginPath();
        ctx.arc(150, 150, 105, 0, Math.PI * 2, false); // Earth orbit
        ctx.stroke();
    }

    renderLine(tidyLine, ctx=this.ctx){
        // from, to.
        /* draw a polyline from a to b. */
        console.log('renderLine', tidyLine)

        let offsetA_X = tidyLine.a.x
        let offsetA_Y = tidyLine.a.y - tidyLine.a.height - (this.dimensions.top)

        let offsetB_X = tidyLine.b.x
        let offsetB_Y = tidyLine.b.y - tidyLine.b.height - (this.dimensions.top)

        ctx.beginPath();
        ctx.arc(offsetA_X
                , offsetA_Y
                , 10
                , 0
                , Math.PI * 2
                , false); // Earth orbit


        ctx.arc(offsetB_X
                , offsetB_Y
                , 10
                , 0
                , Math.PI * 2
                , false); // Earth orbit
        ctx.fill();
    }

    stickCanvasSize(canvas=this.canvas){
        let rect;
        /* Return the result of the bounding box function, else resort
        to the object w/h */
            rect = (canvas.getBoundingClientRect
                    && canvas.getBoundingClientRect()
                    ) || { width: canvas.width, height: canvas.height }
            /*if(rect == undefined) {
                rect = { width: canvas.width , height: canvas.height }
            }*/


        if(rect.width) { canvas.width  = rect.width; }
        if(rect.height) { canvas.height = rect.height; }
        rect.width  = canvas.width;
        rect.height = canvas.height;

        return rect;
    }

}