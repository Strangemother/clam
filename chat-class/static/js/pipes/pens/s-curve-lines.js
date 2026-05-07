const drawSCurveLinesWithTipDirection = function(ctx, lines, color='purple') {
        let defaultLineWidth = 2
        ctx.strokeStyle = color;
        ctx.lineWidth = defaultLineWidth;

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
            ctx.lineWidth = defaultLineWidth
            const o = lineItems[i]

            const dx = o.b.x - o.a.x
            const handle = Math.max(minHandle, Math.abs(dx) * handleFactor)
            const fallbackSenderSign = dx >= 0 ? 1 : -1
            const fallbackReceiverSign = -fallbackSenderSign
            const senderSign = getTipSign(o.senderDirection, fallbackSenderSign)
            const receiverSign = getTipSign(o.receiverDirection, fallbackReceiverSign)

            const c1x = o.a.x + (senderSign * handle)
            const c2x = o.b.x + (receiverSign * handle)
            if(o.obj.width){
                ctx.lineWidth = o.obj.width;
            };

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

    ;penFunctions.drawSCurveLinesWithTipDirection = drawSCurveLinesWithTipDirection;