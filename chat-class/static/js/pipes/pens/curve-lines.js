
 const drawSCurveLines = function(ctx, lines, color='purple') {
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

penFunctions.drawSCurveLines = drawSCurveLines