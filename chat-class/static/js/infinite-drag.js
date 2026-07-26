/**
 * Pan the panel workspace with the middle mouse button and zoom around the
 * pointer wheel position. Panels remain individually draggable through
 * DragSolo; this utility only changes the workspace view.
 */
class InfiniteDrag {
    constructor(selector, itemSelector = '.panel') {
        this.element = typeof selector === 'string'
            ? document.querySelector(selector)
            : selector
        this.itemSelector = itemSelector
        this.dragging = false
        this.lastX = 0
        this.lastY = 0

        if (!this.element) return

        this._onMouseDown = this._onMouseDown.bind(this)
        this._onMouseMove = this._onMouseMove.bind(this)
        this._onMouseUp = this._onMouseUp.bind(this)
        this._onContextMenu = this._onContextMenu.bind(this)
        this.element.addEventListener('mousedown', this._onMouseDown)
        this.element.addEventListener('contextmenu', this._onContextMenu)
    }

    _onContextMenu(event) {
        if (event.button === 1) event.preventDefault()
    }

    _onMouseDown(event) {
        if (event.button !== 1) return
        event.preventDefault()
        event.stopPropagation()
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
        if (event.button !== 1) return
        this.dragging = false
        document.removeEventListener('mousemove', this._onMouseMove)
        document.removeEventListener('mouseup', this._onMouseUp)
        this.dragComplete()
    }

    _applyDelta(dx, dy) {
        for (const node of this.element.querySelectorAll(this.itemSelector)) {
            if (node.classList.contains('no-pan')) continue
            node.style.left = `${(parseFloat(node.style.left) || 0) + dx}px`
            node.style.top = `${(parseFloat(node.style.top) || 0) + dy}px`
        }
        document.dispatchEvent(new CustomEvent('panspace', {
            detail: { position: { dx, dy }, element: this.element }
        }))
    }

    dragComplete() {}

    destroy() {
        if (!this.element) return
        this.element.removeEventListener('mousedown', this._onMouseDown)
        this.element.removeEventListener('contextmenu', this._onContextMenu)
        document.removeEventListener('mousemove', this._onMouseMove)
        document.removeEventListener('mouseup', this._onMouseUp)
    }
}

class ZoomableInfiniteDrag extends InfiniteDrag {
    constructor(selector, itemSelector, options = {}) {
        super(selector, itemSelector)
        this.options = { zoomMode: 'transform', ...options }
        this.scale = 1
        this._onWheel = this._onWheel.bind(this)
        this.element?.addEventListener('wheel', this._onWheel, { passive: false })
    }

    _onWheel(event) {
        if (event.target.closest?.('input, textarea, select, [contenteditable="true"]')) return
        event.preventDefault()

        const previousScale = this.scale
        const nextScale = Math.max(0.35, Math.min(2.5,
            previousScale * (event.deltaY > 0 ? 0.9 : 1.1)))
        const rect = this.element.getBoundingClientRect()
        const originX = event.clientX - rect.left
        const originY = event.clientY - rect.top
        const factor = nextScale / previousScale

        for (const node of this.element.querySelectorAll(this.itemSelector)) {
            if (node.classList.contains('no-pan')) continue
            const left = parseFloat(node.style.left) || 0
            const top = parseFloat(node.style.top) || 0
            node.style.left = `${originX + (left - originX) * factor}px`
            node.style.top = `${originY + (top - originY) * factor}px`
            node.style.transformOrigin = 'top left'
            node.style.transform = `scale(${nextScale})`
        }

        this.scale = nextScale
        document.dispatchEvent(new CustomEvent('zoomspace', {
            detail: {
                mouseX: originX,
                mouseY: originY,
                element: this.element,
                scale: nextScale,
                prevScale: previousScale,
                origin: { x: event.clientX, y: event.clientY }
            }
        }))
    }

    destroy() {
        super.destroy()
        this.element?.removeEventListener('wheel', this._onWheel)
    }
}
