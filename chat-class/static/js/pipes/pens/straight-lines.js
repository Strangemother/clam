
 const drawStraightLines = function(ctx, lines, color='purple') {
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

;penFunctions.drawStraightLines = drawStraightLines;