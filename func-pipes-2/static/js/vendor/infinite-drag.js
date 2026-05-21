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
    itemSelector = 'main > *'
    constructor(selector, itemSelector='.winbox') {
        this.selector = selector
        this.itemSelector = itemSelector
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
        if (event.button == this.DRAG_MOUSE_BUTTON_INDEX) {
            event.preventDefault()
        }
    }

    DRAG_MOUSE_BUTTON_INDEX = 1
    _onMouseDown(event) {
        if (event.button !== this.DRAG_MOUSE_BUTTON_INDEX) return
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
        if (event.button !== this.DRAG_MOUSE_BUTTON_INDEX) return
        this.dragging = false

        document.removeEventListener('mousemove', this._onMouseMove)
        document.removeEventListener('mouseup', this._onMouseUp)

        this.dragComplete()
    }

    dragComplete() {}


    _applyDelta(dx, dy) {
        const nodes = this.element.querySelectorAll(this.itemSelector)
        nodes.forEach(node => {
            if(node.classList.contains('no-pan')) {
                /*
                    This allows dragging but not panning of a div in a space.
                    A User can still drag with this div, using the _right click_
                    pan, but also dragging the target div.
                 */
                return
            }
            const left = parseFloat(node.style.left) || 0
            const top = parseFloat(node.style.top) || 0
            node.style.left = `${left + dx}px`
            node.style.top = `${top + dy}px`
        })

        document.dispatchEvent(new CustomEvent('panspace', {
            detail: {
                position: {dx,dy}
                , element: this.element
            }
        }))
    }

    destroy() {
        this.element.removeEventListener('mousedown', this._onMouseDown)
        this.element.removeEventListener('contextmenu', this._onContextMenu)
        document.removeEventListener('mousemove', this._onMouseMove)
        document.removeEventListener('mouseup', this._onMouseUp)
    }
}


class ZoomableInfiniteDrag extends InfiniteDrag {
    constructor(selector, childSelector, options={}) {
        super(selector, childSelector)
        this.options = Object.assign({
            zoomMode: 'resize',   // 'resize' | 'transform'
        }, options)
        this.panOffsetX = 0
        this.panOffsetY = 0
        this._onWheel = this._onWheel.bind(this)
        this._onDragMove = this._onDragMove.bind(this)
        this.element.addEventListener('wheel', this._onWheel, { passive: false })
        document.addEventListener('dragmove', this._onDragMove)
    }

    _isEditableWheelTarget(target) {
        if(!(target instanceof Element)) {
            return false
        }

        return Boolean(target.closest([
            'input',
            'textarea',
            'select',
            '[contenteditable]:not([contenteditable="false"])',
        ].join(', ')))
    }

    _onWheel(event) {
        if(this._isEditableWheelTarget(event.target)) {
            return
        }

        event.preventDefault()
        this.onWheel(event)
    }

    onWheel(event) {
        const prevScale = this.scale || 1
        this.scale = prevScale * (event.deltaY > 0 ? 0.9 : 1.1)
        this.origin = { x: event.clientX, y: event.clientY }
        this.moveAllNodes(this.scale, prevScale, this.origin)
    }

    dragComplete() {
        this.resetZoomBase()
    }

    _ensureTransformPersistState(el) {
        if(this.options.zoomMode !== 'transform') {
            return
        }

        if(el.dataset.zoomWorldLeft === undefined) {
            el.dataset.zoomWorldLeft = `${parseFloat(el.style.left) || 0}`
        }
        if(el.dataset.zoomWorldTop === undefined) {
            el.dataset.zoomWorldTop = `${parseFloat(el.style.top) || 0}`
        }
        el.dataset.zoomScreenLeft = `${parseFloat(el.style.left) || 0}`
        el.dataset.zoomScreenTop = `${parseFloat(el.style.top) || 0}`
    }

    _onDragMove(event) {
        if(this.options.zoomMode !== 'transform') {
            return
        }

        const node = event?.detail?.node
        if(!(node instanceof HTMLElement)) {
            return
        }
        if(!this.element.contains(node) || !node.matches(this.itemSelector)) {
            return
        }

        this._ensureTransformPersistState(node)

        const scale = this.scale || 1
        const prevLeft = parseFloat(node.dataset.zoomScreenLeft) || 0
        const prevTop = parseFloat(node.dataset.zoomScreenTop) || 0
        const left = parseFloat(node.style.left) || 0
        const top = parseFloat(node.style.top) || 0
        const dx = left - prevLeft
        const dy = top - prevTop

        if(scale !== 1) {
            node.dataset.zoomWorldLeft = `${(parseFloat(node.dataset.zoomWorldLeft) || 0) + (dx / scale)}`
            node.dataset.zoomWorldTop = `${(parseFloat(node.dataset.zoomWorldTop) || 0) + (dy / scale)}`
        } else {
            node.dataset.zoomWorldLeft = `${left}`
            node.dataset.zoomWorldTop = `${top}`
        }

        node.dataset.zoomScreenLeft = `${left}`
        node.dataset.zoomScreenTop = `${top}`
    }

    getPersistedBox(el) {
        const left = parseFloat(el.style.left) || 0
        const top = parseFloat(el.style.top) || 0
        const width = Number.isFinite(parseFloat(el.style.width))
            ? parseFloat(el.style.width)
            : el.offsetWidth
        const height = Number.isFinite(parseFloat(el.style.height))
            ? parseFloat(el.style.height)
            : el.offsetHeight

        if(this.options.zoomMode !== 'transform') {
            return {
                left: `${left}px`,
                top: `${top}px`,
                width: `${width}px`,
                height: `${height}px`,
            }
        }

        this._ensureTransformPersistState(el)

        return {
            left: `${(parseFloat(el.dataset.zoomWorldLeft) || 0) + this.panOffsetX}px`,
            top: `${(parseFloat(el.dataset.zoomWorldTop) || 0) + this.panOffsetY}px`,
            width: `${width}px`,
            height: `${height}px`,
        }
    }

    resetViewState() {
        this.scale = 1
        this.origin = null
        this.panOffsetX = 0
        this.panOffsetY = 0
        this.resetZoomBase()
    }

    _applyDelta(dx, dy) {
        super._applyDelta(dx, dy)

        if(this.options.zoomMode !== 'transform') {
            return
        }

        const scale = this.scale || 1
        if(scale !== 1) {
            this.panOffsetX += dx
            this.panOffsetY += dy
        }

        const nodes = this.element.querySelectorAll(this.itemSelector)
        nodes.forEach(node => {
            if(node.classList.contains('no-pan')) {
                return
            }
            this._ensureTransformPersistState(node)
        })
    }

    snapshotNodeBase(el, containerRect) {
        if (el.dataset.zoomBaseLeft !== undefined) {
            return
        }

        const rect = el.getBoundingClientRect()
        const transformMode = this.options.zoomMode === 'transform'
        const baseLeft = Number.isFinite(parseFloat(el.style.left))
            ? parseFloat(el.style.left)
            : rect.left - containerRect.left
        const baseTop = Number.isFinite(parseFloat(el.style.top))
            ? parseFloat(el.style.top)
            : rect.top - containerRect.top
        const baseWidth = Number.isFinite(parseFloat(el.style.width))
            ? parseFloat(el.style.width)
            : transformMode ? el.offsetWidth : rect.width
        const baseHeight = Number.isFinite(parseFloat(el.style.height))
            ? parseFloat(el.style.height)
            : transformMode ? el.offsetHeight : rect.height

        el.dataset.zoomBaseLeft = baseLeft
        el.dataset.zoomBaseTop = baseTop
        el.dataset.zoomBaseWidth = baseWidth
        el.dataset.zoomBaseHeight = baseHeight
    }

    resetZoomBase() {
        const nodes = this.element.querySelectorAll(this.itemSelector)
        for (let el of nodes) {
            delete el.dataset.zoomBaseLeft
            delete el.dataset.zoomBaseTop
            delete el.dataset.zoomBaseWidth
            delete el.dataset.zoomBaseHeight
        }
    }

    // moveAllNodes() {
    //    // callback.
    // }

    moveAllNodes(scale, prevScale, origin) {
        const rect = this.element.getBoundingClientRect()
        const mouseX = origin.x - rect.left
        const mouseY = origin.y - rect.top
        const transformMode = this.options.zoomMode === 'transform'
        const zoomFactor = prevScale ? (scale / prevScale) : scale

        const nodes = this.element.querySelectorAll(this.itemSelector)
        for (let winName of nodes) {
            // let win = nodes[winName]
            const el = winName

            if(el.classList.contains('no-pan')) {
                continue
            }

            this._ensureTransformPersistState(el)

            const nodeRect = el.getBoundingClientRect()
            const currentLeft = Number.isFinite(parseFloat(el.style.left))
                ? parseFloat(el.style.left)
                : nodeRect.left - rect.left
            const currentTop = Number.isFinite(parseFloat(el.style.top))
                ? parseFloat(el.style.top)
                : nodeRect.top - rect.top
            const currentWidth = Number.isFinite(parseFloat(el.style.width))
                ? parseFloat(el.style.width)
                : (transformMode ? el.offsetWidth : nodeRect.width)
            const currentHeight = Number.isFinite(parseFloat(el.style.height))
                ? parseFloat(el.style.height)
                : (transformMode ? el.offsetHeight : nodeRect.height)

            const newLeft = mouseX + (currentLeft - mouseX) * zoomFactor
            const newTop = mouseY + (currentTop - mouseY) * zoomFactor
            const newWidth = currentWidth * zoomFactor
            const newHeight = currentHeight * zoomFactor

            el.style.left = `${newLeft}px`
            el.style.top = `${newTop}px`
            if(transformMode) {
                el.style.transformOrigin = 'top left'
                el.style.transform = `scale(${scale})`
                el.dataset.zoomScreenLeft = `${newLeft}`
                el.dataset.zoomScreenTop = `${newTop}`
            } else {
                el.style.width = `${newWidth}px`
                el.style.height = `${newHeight}px`
                el.style.transformOrigin = ''
                el.style.transform = ''
            }

            const scalePercent = Math.round(scale * 100 / 10) * 10
            el.className = el.className.replace(/\binf-drag-zoom-scale-\d+\b/g, '')
            el.classList.add(`inf-drag-zoom-scale-${scalePercent}`)

            el.className = el.className.replace(/\bfont-size-\d+(\.\d+)?em\b/g, '')
            if(!transformMode) {
                // Use polyclass for font size management in resize mode.
                const fontSizeScale = ( Math.round(scale * 100 / 10) * .1).toFixed(1)
                el.classList.add(`font-size-${fontSizeScale}em`)
            }
        }


        document.dispatchEvent(new CustomEvent('zoomspace', {
            detail: {
                mouseX
                , mouseY
                , element: this.element
                , scale
                , prevScale
                , origin
            }
        }))
    }

    destroy() {
        super.destroy()
        this.element.removeEventListener('wheel', this._onWheel)
        document.removeEventListener('dragmove', this._onDragMove)
    }

}
