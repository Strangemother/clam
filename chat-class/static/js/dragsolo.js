/**
 * DragSolo.js - A lightweight library for drag-and-drop functionalities.
 *
 * Two main components exist for dragging: the _host_ and the draggables.
 * To use:
 * 1. Initiate a new DragSolo instance.
 * 2. Enable dragging on your desired elements.
 *
 * Example:
 * dragHost = new DragSolo()
 * dragHost.enable('.box')
 * dragHost.enable('h1')
 */

class Draggable {
    tracking = false

    /**
     * Represents a draggable element.
     * @param {HTMLElement} node - The HTML element to be made draggable.
     * @param {DragSolo} host - The DragSolo instance managing this draggable.
     */
    constructor(node, host) {
        this.node = node;
        this.host = host;
        this.onChangeHooks = []
        this.space = {
            clientY: 0
            , clientX: 0
            , offsetX: 0
            , offsetY: 0
        }
        this.dragParent = null
    }

    /**
     * Enables dragging for all elements matching the given selector.
     * @param {string} selector - The CSS selector to match elements.
     */
    static enable(selector) {
        let nodes = document.querySelectorAll(selector)
        for(let node of nodes) {
            if(node.dataset.draggable == undefined)  {
                this.add(node)
            }
        }
    }

    /**
     * Adds a new draggable element.
     * @param {HTMLElement} node - The HTML element to be made draggable.
     */
    static add(node) {
        node.dataset.draggable = 'draggable'
        node.dataset.draggableId = Math.random().toString(32).slice(2, 6)

        this.host.nodes[node.dataset.draggableId] = new Draggable(node)
    }

    /**
     * Gets the current position of the draggable element.
     * @returns {Position} - The current position.
     */
    get position(){
        if(this.tracking){
            return new Position(this.space.clientX, this.space.clientY)
        }

        return this.getLivePosition()
    }

    /**
     * Sets the position of the draggable element.
     * @param {Position} pos - The new position.
     */
    setPosition(pos) {
        this.setNodeXY(pos.x, pos.y)
    }

    /**
     * Registers a callback function to be called when the draggable element changes position.
     * @param {function} func - The callback function.
     */
    onChange(func) {
        this.onChangeHooks.push(func)
    }

    /**
     * Gets the live position of the draggable element.
     * @returns {Position} - The current position.
     */
    getLivePosition(){
        let rect = this.node.getBoundingClientRect()

        return (function(v){ let {x,y} = v; return {x,y} })(rect)
    }

    /**
     * Handles the mousedown event.
     * @param {Event} e - The mousedown event.
     * @param {HTMLElement} node - The target element of the event.
     */
    mousedownEvent(e, node) {
        // copy the node position into this position when moved.
        if(this.node == node) {
            if(e.target.classList.contains('dragsolo-bubble')) {
                // ignore bubbled events.
                return
            }
            let rect = node.getBoundingClientRect()
            this.tracking = true
            console.log('mousedown', this.id())
            this.host.tracking.add(this)
            this.dragParent = node.offsetParent || document.documentElement
            this.node.dataset.dragging = 'dragging'
            Object.assign(this.space, {
                clientX: e.clientX
                , clientY: e.clientY
                , offsetX: e.clientX - rect.left
                , offsetY: e.clientY - rect.top
            })
            this.presentSpaceXY()
        } else {
            console.log('Will not mousedownEvent', node, this.node)
        }
    }

    /**
     * Handles the mousemove event.
     * @param {Event} e - The mousemove event.
     */
    mousemoveEvent(e) {
        if(this.tracking) {
            Object.assign(this.space, {
                    clientY: e.clientY
                    , clientX: e.clientX
                })
            this.presentSpaceXY()
            // console.log('move', this.clientX, this.clientY)
        }
    }

    /**
     * Gets the ID of the draggable element.
     * @returns {string} - The ID.
     */
    id() {
        return this.node.dataset.draggableId
    }

    /**
     * Handles the mouseup event.
     * @param {Event} e - The mouseup event.
     */
    mouseupEvent(event) {
        let node = event.target
        if(this.tracking) {
            // console.log('mouseup', this.id(), 'onto', node)
            // console.log('mouseup', this.node, this.space.clientX, this.space.clientY)
            this.node.dataset.dragging = ''
            // this.presentSpaceXY()
            this.tracking = false
            this.dragParent = null
            this.host.tracking.delete(this)
        }
    }

    /**
     * Updates the position of the draggable element based on its current space.
     */
    presentSpaceXY() {
        let dragParent = this.dragParent || this.node.offsetParent || document.documentElement
        let parentOrigin = getParentClientOrigin(dragParent)
        let x = this.space.clientX - parentOrigin.left - this.space.offsetX
        let y = this.space.clientY - parentOrigin.top - this.space.offsetY
        this.setNodeXY(x, y)

        document.dispatchEvent(new CustomEvent('dragmove', {
            detail: {
                position: {x,y}
                , dragParent
                , parentOrigin
                , space: this.space
                , node: this.node
                , draggable: this
            }
        }))
        for(let cf of this.onChangeHooks) {
            cf({x,y})
        }

    }

    /**
     * Sets the X and Y position of the draggable element.
     * @param {number} x - The X position.
     * @param {number} y - The Y position.
     */
    setNodeXY(x,y) {
        // this.position.x = x
        // this.position.y = y
        this.node.style.top = `${y}px`
        this.node.style.left = `${x}px`
    }
}


const getParentClientOrigin = function(dragParent) {
    dragParent = dragParent || document.documentElement
    let parentRect = dragParent.getBoundingClientRect()

    return {
        left: parentRect.left + dragParent.clientLeft - dragParent.scrollLeft,
        top: parentRect.top + dragParent.clientTop - dragParent.scrollTop
    }
}


const isResizeHandleEvent = function(node, event) {
    if(node == null) {
        return false
    }

    let style = window.getComputedStyle(node)
    if(style.resize == 'none') {
        return false
    }

    let rect = node.getBoundingClientRect()
    let handleSize = 18
    let nearRight = event.clientX >= (rect.right - handleSize)
    let nearBottom = event.clientY >= (rect.bottom - handleSize)
    let nearLeft = event.clientX <= (rect.left + handleSize)
    let nearTop = event.clientY <= (rect.top + handleSize)

    if(style.resize == 'both') {
        return nearRight && nearBottom
    }

    if(style.resize == 'horizontal') {
        return nearRight || nearLeft
    }

    if(style.resize == 'vertical') {
        return nearBottom || nearTop
    }

    return false
}


class DragSolo {

    /**
     * Represents the main drag manager.
     * @param {HTMLElement} [parent=document] - The parent element for the draggables.
     */
    constructor(parent=document) {
        this.parent = parent
        this.nodes = {}
        this.tracking = new Set
        this.mouseTrack = false
        this.listening = false
    }

    /**
     * Enables dragging for the given elements or selectors.
     * @param {string|HTMLElement[]} selector - The CSS selector or list of elements.
     * @returns {Draggable[]} - The list of draggables created.
     */
    enable(selector) {
        let nodes = [selector]
        let r = []
        if(typeof(selector) == 'string') {
            nodes = document.querySelectorAll(selector)
        }

        for(let node of nodes) {
            if(node.dataset.draggable == undefined)  {
                let d = this.add(node)
                r.push(d)
            }
        }

        if(this.listening != true) {
            this.listen()
        }
        return r
    }

    /**
     * Adds a new draggable element.
     * @param {HTMLElement} node - The HTML element to be made draggable.
     * @returns {Draggable} - The draggable created.
     */
    add(node) {
        node.dataset.draggable = 'draggable'
        node.dataset.draggableId = Math.random().toString(32).slice(2, 10)
        return this.nodes[node.dataset.draggableId] = new Draggable(node, this)
    }

    /**
     * Starts listening for drag events on the host target.
     * @param {HTMLElement} [hostTarget=undefined] - The target element to listen on.
     */
    listen(hostTarget=undefined) {
        let host = this;
        hostTarget = hostTarget || this.parent
        let body = document.body

        let mousedown = function(event){
            let node = event.target.closest('[data-draggable-id]') || event.target
            // console.log('mouseDown', node)
            let dn = host.nodes[node.dataset.draggableId]
            if(dn != undefined) {
                if(isResizeHandleEvent(dn.node, event)) {
                    host.mouseTrack = false
                    body.dataset.draghost='resize'
                    return
                }

                host.mouseTrack = true
                // console.log('Drag', dn)
                dn.mousedownEvent(event, node)
                body.dataset.draghost='mousedown'
            }

            // console.log(event.target, event.currentTarget)
        }

        let mousemove = function(event){
            // console.log('mousemove')
            if(host.mouseTrack == false){
                return
            }

            let node = event.target
            // let dn = host.nodes[node]
            // console.log(host.tracking.size)
            let isTracking = false
            for(let dn of host.tracking) {
                dn.mousemoveEvent(event)
                isTracking = true
                // console.log(event.target, event.currentTarget)
            }

            if (isTracking){
                body.dataset.draghost='mousemove'
            }
        }

        let mouseup = function(event){
            host.mouseTrack = false
            let node = event.target
            // console.log('mouseUp', node)

            let isTracking = false
            for(let dn of host.tracking) {
                isTracking = true
                dn.mouseupEvent(event)
                // console.log(event.target, event.currentTarget)
            }
            if (isTracking){
                body.dataset.draghost='mouseup'
            }
        }


        hostTarget.addEventListener('click', function(event){
            let node = event.target
            // console.log('click', node)
        })

        hostTarget.addEventListener('mousemove', mousemove)
        hostTarget.addEventListener('mouseup', mouseup)
        hostTarget.addEventListener('mousedown', mousedown)

        this.listening = true
    }
}


const stickAll = function(selector) {
    /* given a selector, write the existing real position
    of all nodes so they can be tracked from their initial position.

    This allows divs to have a page position, and then activate dragging will not cause them to jump to the top-left corner.
    */

    let nodes = [selector];
    if(typeof(selector) == 'string') {
        nodes = Array.from(document.querySelectorAll(selector))
    }
    let snapshots = nodes.map(function(node) {
        let rect = node.getBoundingClientRect()
        let parentOrigin = getParentClientOrigin(node.offsetParent || document.documentElement)

        return {
            node,
            x: rect.left - parentOrigin.left,
            y: rect.top - parentOrigin.top,
            width: rect.width,
            height: rect.height
        }
    })

    for(let snapshot of snapshots) {
        // snapshot.node.style.position = 'absolute'
        snapshot.node.style.left = `${snapshot.x}px`
        snapshot.node.style.top = `${snapshot.y}px`
        snapshot.node.style.width = `${snapshot.width}px`
        snapshot.node.style.height = `${snapshot.height}px`
        // snapshot.node.style.margin = '0'
        snapshot.node.dataset.dragsoloSticked = 'true'
    }

    return snapshots
}

// Initialization code for DragSolo based on script attributes.
document.addEventListener("DOMContentLoaded", (event) => {
    let selectors = []
    let nodes = document.querySelectorAll('script[dragsolo-selector]')
    for(let node of nodes) {
        // let node = nodes[i]
        if(node) {
            let selector = node.getAttribute('dragsolo-selector')
            selectors.push(selector)
        }
    }
    if(selectors.length > 0) {
        let dh = window.dragHost = new DragSolo()
        for(let s of selectors) {
            dh.enable(s)
        }
    }
});