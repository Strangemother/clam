
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

        let _id = `${obj.sender.label}-${obj.sender.pipIndex}-${obj.receiver.label}-${obj.receiver.pipIndex}`

        let store = pipeData.connections[_id];

        if(store == undefined) {
            // make a new one
            console.log('Stashed', _id)
            pipeData.connections[_id] = {
                obj
                , senderUnit
                , receiverUnit
            }
        } else {
            // Append to existing one
            console.log('Already have connection', _id, store)
            // The sender unit and receiver unit should be the same, but the pipIndex may differ, so we add these.
            
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
        /* Re-read the canvas position here so all point math is done once,
           converting viewport-absolute DOMRect coords into canvas-local ones
           before anything is stored or drawn.
           scaleX/Y corrects for any mismatch between the canvas attribute
           dimensions and its CSS-rendered size — without this, offsets grow
           increasingly wrong the further a node is from the origin. */
        const cvs = this.layers[1].canvas
        const canvasRect = cvs.getBoundingClientRect()
        const scaleX = cvs.width  / canvasRect.width
        const scaleY = cvs.height / canvasRect.height

        for(let _id in pipeData.connections) {
            let conn = pipeData.connections[_id]

            let senderNode = conn.senderUnit.node
            let receiverNode = conn.receiverUnit.node

            let sr = senderNode.getBoundingClientRect()
            let rr = receiverNode.getBoundingClientRect()

            // Canvas-local centre points
            let a = {
                x: (sr.x + sr.width  * 0.5 - canvasRect.left) * scaleX
                , y: (sr.y + sr.height * 0.5 - canvasRect.top) * scaleY
            }
            let b = {
                x: (rr.x + rr.width  * 0.5 - canvasRect.left) * scaleX
                , y: (rr.y + rr.height * 0.5 - canvasRect.top) * scaleY
            }

            console.log('From', conn.senderUnit, 'to', conn.receiverUnit)
            this.drawLine(_id, a, b)
        }

    }

    drawLine(_id, a, b) {
        console.log('From', a, 'to', b)

        let tidyLine = { _id, a, b }
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

        this.straightLine(tidyLine, ctx)
    }

    straightLine(tidyLine, ctx=this.ctx){
        
        // Points are already canvas-local, computed in renderConnections.
        let offsetA_X = tidyLine.a.x
        let offsetA_Y = tidyLine.a.y

        let offsetB_X = tidyLine.b.x
        let offsetB_Y = tidyLine.b.y

        // Dots at each end
        ctx.beginPath();
        ctx.arc(offsetA_X, offsetA_Y, 5, 0, Math.PI * 2, false);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(offsetB_X, offsetB_Y, 5, 0, Math.PI * 2, false);
        ctx.fill();

        // Line between them
        ctx.beginPath();
        ctx.moveTo(offsetA_X, offsetA_Y);
        ctx.lineTo(offsetB_X, offsetB_Y);
        ctx.strokeStyle = 'purple';
        ctx.lineWidth = 3;
        ctx.stroke();
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