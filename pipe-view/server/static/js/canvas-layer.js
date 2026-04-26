
/* Store incoming connection, for future storage */
const pipeData = {
    raw: []
    , connections: {}
}

const PERF_DEBUG = false
const perfLog = PERF_DEBUG ? console.log.bind(console) : ()=>{}

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
        if(obj?.sender == undefined || obj?.receiver == undefined) {
            console.error('Cannot connect without sender/receiver payload.', obj)
            return
        }

        perfLog('connectNodes', obj)
        const resolvedLine = this.resolveLineConfig(obj)
        obj.line = { ...(obj.line || {}), ...resolvedLine }
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
            perfLog('Stashed', _id)
            pipeData.connections[_id] = {
                obj
                , senderUnit
                , receiverUnit
            }
        } else {
            // Append to existing one
            perfLog('Already have connection', _id, store)
            // The sender unit and receiver unit should be the same, but the pipIndex may differ, so we add these.

        }

    }
    resolveLineConfig(obj={}) {
        const line = obj.line || {}
        const style = obj.style || {}

        const color = line.color ?? style.color ?? obj.color
        const design = line.design
                        ?? line.style
                        ?? style.design
                        ?? style.lineDesign
                        ?? obj.lineDesign
                        ?? obj.lineStyle

        return { color, design }
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
        const pointCache = new Map()

        const getCenter = (node) => {
            let point = pointCache.get(node)
            if(point != undefined) {
                return point
            }

            const rect = node.getBoundingClientRect()
            point = {
                x: (rect.x + rect.width  * 0.5 - canvasRect.left) * scaleX
                , y: (rect.y + rect.height * 0.5 - canvasRect.top) * scaleY
            }
            pointCache.set(node, point)
            return point
        }

        for(let _id in pipeData.connections) {
            let conn = pipeData.connections[_id]
            let senderDirection = conn.obj?.sender?.direction
            let receiverDirection = conn.obj?.receiver?.direction

            let senderUnit = conn.senderUnit
            let receiverUnit = conn.receiverUnit

            // Canonicalize orientation at draw-time so we always render
            // outbound -> inbound regardless how the user performed the drag.
            if(senderDirection == 'inbound' && receiverDirection == 'outbound') {
                senderUnit = conn.receiverUnit
                receiverUnit = conn.senderUnit
                senderDirection = 'outbound'
                receiverDirection = 'inbound'
            }

            let senderNode = senderUnit.node
            let receiverNode = receiverUnit.node

            let a = getCenter(senderNode)
            let b = getCenter(receiverNode)
            let lineConfig = conn.obj?.line || {}

            perfLog('From', senderUnit, 'to', receiverUnit)
            this.drawLine(_id, a, b, {
                senderDirection,
                receiverDirection,
                lineColor: lineConfig.color,
                lineDesign: lineConfig.design
            })
        }

    }

    drawLine(_id, a, b, directions={}) {
        perfLog('From', a, 'to', b)

        let tidyLine = this.layers[1].lines[_id]
        if(tidyLine == undefined) {
            tidyLine = {
                _id,
                a,
                b,
                senderDirection: directions.senderDirection,
                receiverDirection: directions.receiverDirection,
                lineColor: directions.lineColor,
                lineDesign: directions.lineDesign
            }
            perfLog('Installing line.')
            this.layers[1].addLine(tidyLine)
            return
        }

        tidyLine.a = a
        tidyLine.b = b
        tidyLine.senderDirection = directions.senderDirection
        tidyLine.receiverDirection = directions.receiverDirection
        tidyLine.lineColor = directions.lineColor
        tidyLine.lineDesign = directions.lineDesign
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
        this.lines = {}
        this.lineStyle = 'curve-tip'
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
        const frameStart = PERF_DEBUG ? performance.now() : 0
        this.clear(ctx)
        perfLog('renderFrame', delta)

        const lineItems = this.toLineArray(this.lines)
        if(lineItems.length == 0) {
            return
        }

        let groups = this.groupLinesByDesignAndColor(lineItems)
        for(let groupKey in groups) {
            let group = groups[groupKey]
            if(group.design == 'straight') {
                this.drawStraightLines(ctx, group.lines, group.color)
            } else if(group.design == 'curve') {
                this.drawSCurveLines(ctx, group.lines, group.color)
            } else {
                this.drawSCurveLinesWithTipDirection(ctx, group.lines, group.color)
            }
        }

        if(PERF_DEBUG) {
            perfLog('frame(ms)', (performance.now() - frameStart).toFixed(2), 'lines', lineItems.length)
        }
    }

    toLineArray(lines=this.lines) {
        if(lines == undefined) {
            return []
        }

        if(Array.isArray(lines)) {
            return lines
        }

        return Object.values(lines)
    }

    getLineDesign(line) {
        const design = line?.lineDesign ?? line?.design ?? line?.lineStyle ?? this.lineStyle
        if(design == 'straight' || design == 'curve' || design == 'curve-tip') {
            return design
        }

        return this.lineStyle
    }

    getLineColor(line) {
        return line?.lineColor ?? line?.color ?? 'purple'
    }

    groupLinesByDesignAndColor(lines) {
        let groups = {}
        for(let i = 0; i < lines.length; i++) {
            let line = lines[i]
            let design = this.getLineDesign(line)
            let color = this.getLineColor(line)
            let key = `${design}::${color}`

            if(groups[key] == undefined) {
                groups[key] = {
                    design,
                    color,
                    lines: []
                }
            }

            groups[key].lines.push(line)
        }

        return groups
    }

    drawStraightLines(ctx=this.ctx, lines=this.lines, color='purple') {
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;

        const lineItems = this.toLineArray(lines)
        ctx.beginPath();
        for(let i = 0; i < lineItems.length; i++) {
            const o = lineItems[i]
            ctx.moveTo(o.a.x, o.a.y)
            ctx.lineTo(o.b.x, o.b.y)
        }
        ctx.stroke();

        ctx.beginPath();
        for(let i = 0; i < lineItems.length; i++) {
            const o = lineItems[i]
            ctx.moveTo(o.a.x + 5, o.a.y)
            ctx.arc(o.a.x, o.a.y, 5, 0, Math.PI * 2, false)

            ctx.moveTo(o.b.x + 5, o.b.y)
            ctx.arc(o.b.x, o.b.y, 5, 0, Math.PI * 2, false)
        }
        ctx.fill();
    }

    drawSCurveLines(ctx=this.ctx, lines=this.lines, color='purple') {
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;

        const lineItems = this.toLineArray(lines)
        const minHandle = 24
        const handleFactor = 0.35

        ctx.beginPath();
        for(let i = 0; i < lineItems.length; i++) {
            const o = lineItems[i]
            const dx = o.b.x - o.a.x
            const sign = dx >= 0 ? 1 : -1
            const handle = Math.max(minHandle, Math.abs(dx) * handleFactor)
            const c1x = o.a.x + (sign * handle)
            const c2x = o.b.x - (sign * handle)

            ctx.moveTo(o.a.x, o.a.y)
            ctx.bezierCurveTo(c1x, o.a.y, c2x, o.b.y, o.b.x, o.b.y)
        }
        ctx.stroke();

        ctx.beginPath();
        for(let i = 0; i < lineItems.length; i++) {
            const o = lineItems[i]
            ctx.moveTo(o.a.x + 5, o.a.y)
            ctx.arc(o.a.x, o.a.y, 5, 0, Math.PI * 2, false)

            ctx.moveTo(o.b.x + 5, o.b.y)
            ctx.arc(o.b.x, o.b.y, 5, 0, Math.PI * 2, false)
        }
        ctx.fill();
    }

    drawSCurveLinesWithTipDirection(ctx=this.ctx, lines=this.lines, color='purple') {
        ctx.strokeStyle = color;
        ctx.lineWidth = 3;

        const lineItems = this.toLineArray(lines)
        const minHandle = 24
        const handleFactor = 0.35

        const getTipSign = (direction, fallbackSign) => {
            if(direction == 'outbound') {
                return 1
            }
            if(direction == 'inbound') {
                return -1
            }
            return fallbackSign
        }

        ctx.beginPath();
        for(let i = 0; i < lineItems.length; i++) {
            const o = lineItems[i]
            const dx = o.b.x - o.a.x
            const handle = Math.max(minHandle, Math.abs(dx) * handleFactor)
            const fallbackSenderSign = dx >= 0 ? 1 : -1
            const fallbackReceiverSign = -fallbackSenderSign
            const senderSign = getTipSign(o.senderDirection, fallbackSenderSign)
            const receiverSign = getTipSign(o.receiverDirection, fallbackReceiverSign)

            const c1x = o.a.x + (senderSign * handle)
            const c2x = o.b.x + (receiverSign * handle)

            ctx.moveTo(o.a.x, o.a.y)
            ctx.bezierCurveTo(c1x, o.a.y, c2x, o.b.y, o.b.x, o.b.y)
        }
        ctx.stroke();

        ctx.beginPath();
        for(let i = 0; i < lineItems.length; i++) {
            const o = lineItems[i]
            ctx.moveTo(o.a.x + 5, o.a.y)
            ctx.arc(o.a.x, o.a.y, 5, 0, Math.PI * 2, false)

            ctx.moveTo(o.b.x + 5, o.b.y)
            ctx.arc(o.b.x, o.b.y, 5, 0, Math.PI * 2, false)
        }
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