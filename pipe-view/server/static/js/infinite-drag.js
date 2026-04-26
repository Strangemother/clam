/**
 Infinite Drag
 
 This is a simple addon for a div to allow _infinite_ dragging of the space.
 Divs within the space are moved with the drag, but the space itself is infinite.

 For now the easiest implementation is _right click drag_, where the user
 right click and holds, pulling the space in the direction of the drag. The divs within the space are moved with the drag, but the space itself is infinite.

    The implementation is simple: on right click, we add a mousemove listener to the document. On mousemove, we calculate the delta of the mouse movement and apply that delta to all divs within the space. On mouseup, we remove the mousemove listener.

Currently the divs within are maintained by WinBox, so we can just query for all WinBox divs and apply the delta to them.
In the future, we may want to maintain our own list of divs within the space, but for now this is sufficient.

example

    <div id="infinite-space" class="infinite-space">
        <div class="winbox" id="win1">Window 1</div>
        <div class="winbox" id="win2">Window 2</div>
    </div>

    const infiniteDrag = new InfiniteDrag('#infinite-space')
    // then right click and drag within the #infinite-space - all the divs within will move with the drag, but the space itself is infinite. 
 */

class InfiniteDrag {
    constructor(selector) {
        this.selector = selector
        this.element = typeof selector === 'string'
            ? document.querySelector(selector)
            : selector
        this.dragging = false
        this.lastX = 0
        this.lastY = 0

        this._onMouseDown = this._onMouseDown.bind(this)
        this._onMouseMove = this._onMouseMove.bind(this)
        this._onMouseUp = this._onMouseUp.bind(this)
        this._onContextMenu = this._onContextMenu.bind(this)

        this.element.addEventListener('mousedown', this._onMouseDown)
        this.element.addEventListener('contextmenu', this._onContextMenu)
    }

    _onContextMenu(event) {
        // Suppress context menu so right-click drag feels clean
        event.preventDefault()
    }

    _onMouseDown(event) {
        if (event.button !== 2) return
        event.preventDefault()
        this.dragging = true
        this.lastX = event.clientX
        this.lastY = event.clientY
        document.addEventListener('mousemove', this._onMouseMove)
        document.addEventListener('mouseup', this._onMouseUp)
    }

    _onMouseMove(event) {
        if (!this.dragging) return
        const dx = event.clientX - this.lastX
        const dy = event.clientY - this.lastY
        this.lastX = event.clientX
        this.lastY = event.clientY
        this._applyDelta(dx, dy)
    }

    _onMouseUp(event) {
        if (event.button !== 2) return
        this.dragging = false
        document.removeEventListener('mousemove', this._onMouseMove)
        document.removeEventListener('mouseup', this._onMouseUp)
        
        this.dragComplete()
    }

    dragComplete() {}


    _applyDelta(dx, dy) {
        const nodes = this.element.querySelectorAll('.winbox')
        nodes.forEach(node => {
            const left = parseFloat(node.style.left) || 0
            const top = parseFloat(node.style.top) || 0
            node.style.left = `${left + dx}px`
            node.style.top = `${top + dy}px`
        })
    }

    destroy() {
        this.element.removeEventListener('mousedown', this._onMouseDown)
        this.element.removeEventListener('contextmenu', this._onContextMenu)
        document.removeEventListener('mousemove', this._onMouseMove)
        document.removeEventListener('mouseup', this._onMouseUp)
    }
}
