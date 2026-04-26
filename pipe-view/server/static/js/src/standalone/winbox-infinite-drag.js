/*
Extends ZoomableInfiniteDrag for a WinBox managed UI.
*/

class WinboxInfiniteDrag extends ZoomableInfiniteDrag {
    dragComplete() {
        // rebind all winbox move events to trigger a redraw, since the positions have changed
        // winbox.move("center", "center");
        // pipesTool.app.windowMap['apples'].move('100px', '100px')
        for (let winName in pipesTool.app.windowMap) {
            let win = pipesTool.app.windowMap[winName]
            // Read the actual CSS position we moved to, not WinBox's stale internal values.
            const left = parseFloat(win.g.style.left) || 0
            const top = parseFloat(win.g.style.top) || 0
            if(left > 0 && top > 0) {
                // winbox force locks 0,0
                // so only reseat visible windows. Otherwise offscreen windows will be snapped to 0,0.
                win.move(left, top)
            }
        }
        this.resetZoomBase()
    }

    moveAllNodes(scale, prevScale, origin) {
        const rect = this.element.getBoundingClientRect()
        const mouseX = origin.x - rect.left
        const mouseY = origin.y - rect.top

        for (let winName in pipesTool.app.windowMap) {
            let win = pipesTool.app.windowMap[winName]
            const el = win.g

            // Snapshot the unzoomed position+size the first time we see this node,
            // or whenever the zoom is reset to 1 externally.
            if (el.dataset.zoomBaseLeft === undefined) {
                const left = parseFloat(el.style.left) || 0
                const top  = parseFloat(el.style.top)  || 0
                if (left === 0 && top === 0) continue  // not yet positioned

                el.dataset.zoomBaseLeft   = left
                el.dataset.zoomBaseTop    = top
                el.dataset.zoomBaseWidth  = el.offsetWidth
                el.dataset.zoomBaseHeight = el.offsetHeight
            }

            // Always derive from the stored base — never from the current scaled value.
            // Use the live mouse position each tick so the pivot follows the cursor.
            const baseLeft   = parseFloat(el.dataset.zoomBaseLeft)
            const baseTop    = parseFloat(el.dataset.zoomBaseTop)
            const baseWidth  = parseFloat(el.dataset.zoomBaseWidth)
            const baseHeight = parseFloat(el.dataset.zoomBaseHeight)

            const newLeft   = mouseX + (baseLeft - mouseX) * scale
            const newTop    = mouseY + (baseTop  - mouseY) * scale
            const newWidth  = baseWidth  * scale
            const newHeight = baseHeight * scale

            win.move(newLeft, newTop)
            win.resize(newWidth, newHeight)

            const scalePercent = Math.round(scale * 100 / 10) * 10
            el.className = el.className.replace(/\binf-drag-zoom-scale-\d+\b/g, '')
            el.classList.add(`inf-drag-zoom-scale-${scalePercent}`)

            // Note: we could also apply a CSS transform: scale() here instead of resizing, but that would make the content blurry. Resizing keeps it crisp.
            //Use polyclass for font size management
            const fontSizeScale = ( Math.round(scale * 100 / 10) * .1).toFixed(1)
            el.className = el.className.replace(/\bfont-size-\d+(\.\d+)?em\b/g, '')
            el.classList.add(`font-size-${fontSizeScale}em`)
        }
    }

    // Call this after a drag completes or any external move, so the stored base
    // positions are refreshed to match the new layout at the current scale.
    resetZoomBase() {
        for (let winName in pipesTool.app.windowMap) {
            const el = pipesTool.app.windowMap[winName].g
            delete el.dataset.zoomBaseLeft
            delete el.dataset.zoomBaseTop
            delete el.dataset.zoomBaseWidth
            delete el.dataset.zoomBaseHeight
        }
        this.scale = 1
    }

}
