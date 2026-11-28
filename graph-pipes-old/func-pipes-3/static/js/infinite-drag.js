class WorkspaceInteractions {
    constructor(workspace, itemSelector) {
        this.workspace = workspace
        this.itemSelector = itemSelector
        this.scale = 1
        this.panX = 0
        this.panY = 0
        this.nodeDrag = null
        this.panDrag = null

        workspace.addEventListener('mousedown', this.onMouseDown.bind(this))
        workspace.addEventListener('wheel', this.onWheel.bind(this), { passive: false })
        document.addEventListener('mousemove', this.onMouseMove.bind(this))
        document.addEventListener('mouseup', this.onMouseUp.bind(this))
    }

    get items() {
        return [...this.workspace.querySelectorAll(this.itemSelector)]
    }

    onMouseDown(event) {
        if (event.button === 1) {
            event.preventDefault()
            this.panDrag = {
                x: event.clientX,
                y: event.clientY,
            }
            this.workspace.classList.add('is-panning')
            return
        }

        if (event.button !== 0) return

        const item = event.target.closest(this.itemSelector)
        if (!item) return

        event.preventDefault()
        this.nodeDrag = {
            item,
            x: event.clientX,
            y: event.clientY,
        }
        item.classList.add('is-dragging')
    }

    onMouseMove(event) {
        if (this.panDrag) {
            const dx = event.clientX - this.panDrag.x
            const dy = event.clientY - this.panDrag.y
            this.panDrag.x = event.clientX
            this.panDrag.y = event.clientY
            this.panX += dx
            this.panY += dy
            this.render()
            return
        }

        if (!this.nodeDrag) return

        const dx = (event.clientX - this.nodeDrag.x) / this.scale
        const dy = (event.clientY - this.nodeDrag.y) / this.scale
        this.nodeDrag.x = event.clientX
        this.nodeDrag.y = event.clientY
        const item = this.nodeDrag.item
        item.dataset.x = `${(Number(item.dataset.x) || 0) + dx}`
        item.dataset.y = `${(Number(item.dataset.y) || 0) + dy}`
        this.render()
    }

    onMouseUp(event) {
        if (event.button === 1 && this.panDrag) {
            this.panDrag = null
            this.workspace.classList.remove('is-panning')
        }

        if (event.button === 0 && this.nodeDrag) {
            this.nodeDrag.item.classList.remove('is-dragging')
            this.nodeDrag = null
        }
    }

    onWheel(event) {
        if (event.target.closest('button, input, textarea, select')) return

        event.preventDefault()
        const bounds = this.workspace.getBoundingClientRect()
        const pointerX = event.clientX - bounds.left
        const pointerY = event.clientY - bounds.top
        const previousScale = this.scale
        const factor = event.deltaY < 0 ? 1.1 : 0.9
        this.scale = Math.max(0.5, Math.min(2.5, this.scale * factor))

        const ratio = this.scale / previousScale
        this.panX = pointerX - (pointerX - this.panX) * ratio
        this.panY = pointerY - (pointerY - this.panY) * ratio
        this.render()
    }

    render() {
        this.workspace.style.setProperty('--workspace-scale', this.scale)
        this.workspace.style.setProperty('--workspace-pan-x', `${this.panX}px`)
        this.workspace.style.setProperty('--workspace-pan-y', `${this.panY}px`)
        for (const item of this.items) {
            const x = Number(item.dataset.x) || 0
            const y = Number(item.dataset.y) || 0
            item.style.transform = `translate(${this.panX + x * this.scale}px, ${this.panY + y * this.scale}px) scale(${this.scale})`
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const workspace = document.querySelector('[data-workspace]')
    if (!workspace) return

    const interactions = new WorkspaceInteractions(workspace, '[data-workspace-item]')
    interactions.render()
    window.workspaceInteractions = interactions
})
