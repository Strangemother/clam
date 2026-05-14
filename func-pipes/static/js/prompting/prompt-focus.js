/*
  prompt-focus.js
  ─────────────────────────────────────────────────────────────────────────────
  Focus mode for prompting panels.

  Double-click a panel header to pin a small working set:
  - the selected panel is centered
  - direct inputs are arranged to the left
  - direct outputs are arranged to the right

  Focused panels keep drag enabled, but are excluded from space pan/zoom and
  can be restored to their original positions with clearFocusedPanels().
*/

const FocusMethods = {

    togglePanelFocus(panel) {
        if (!panel) return
        if (this.focusPinState.active && this.focusPinState.centerId === panel.id) {
            this.clearFocusedPanels()
            return
        }
        this.pinFocusedPanels(panel)
    },

    pinFocusedPanels(centerPanel) {
        if (!centerPanel) return

        if (this.focusPinState.active) {
            this.clearFocusedPanels()
        }

        const { inputs, outputs } = this._getFocusNeighbors(centerPanel)
        const focusedPanels = [centerPanel, ...inputs, ...outputs]

        focusedPanels.forEach(panel => this._snapshotFocusRestore(panel))

        this.focusPinState = {
            active:   true,
            centerId: centerPanel.id,
            panelIds: focusedPanels.map(panel => panel.id),
        }

        nextTick(() => {
            this._layoutFocusedPanels(centerPanel, inputs, outputs)
        })
    },

    clearFocusedPanels() {
        const focusedPanels = this.panels.filter(panel => panel._focusPinned || panel._focusRestore)
        focusedPanels.forEach(panel => {
            const el = this._getPanelElement(panel)
            const restore = panel._focusRestore
            if (el && restore) {
                el.style.left = restore.left
                el.style.top = restore.top
            }
            panel._focusPinned = false
            panel._focusRole = ''
            panel._focusRestore = null
        })

        this.focusPinState = {
            active:   false,
            centerId: null,
            panelIds: [],
        }

        if (typeof dispatchRequestDrawEvent !== 'undefined') {
            dispatchRequestDrawEvent()
        }
    },

    resetFocusPinState() {
        this.panels.forEach(panel => {
            panel._focusPinned = false
            panel._focusRole = ''
            panel._focusRestore = null
        })
        this.focusPinState = {
            active:   false,
            centerId: null,
            panelIds: [],
        }
    },

    _getFocusNeighbors(centerPanel) {
        const centerId = String(centerPanel.id)
        if (typeof pipesWalker === 'undefined' || !pipesWalker) {
            return { inputs: [], outputs: [] }
        }

        const seen = new Set([centerId])
        const inputs = []
        const outputs = []

        for (const id of pipesWalker.getIncomingIds(centerId) || []) {
            const panel = this.panels.find(p => String(p.id) === String(id))
            if (!panel || seen.has(String(panel.id))) continue
            seen.add(String(panel.id))
            inputs.push(panel)
        }

        for (const id of pipesWalker.getOutgoingIds(centerId) || []) {
            const panel = this.panels.find(p => String(p.id) === String(id))
            if (!panel || seen.has(String(panel.id))) continue
            seen.add(String(panel.id))
            outputs.push(panel)
        }

        return { inputs, outputs }
    },

    _snapshotFocusRestore(panel) {
        if (!panel || panel._focusRestore) return
        const el = this._getPanelElement(panel)
        if (!el) return
        panel._focusRestore = {
            left: el.style.left || `${el.offsetLeft}px`,
            top:  el.style.top  || `${el.offsetTop}px`,
        }
    },

    _layoutFocusedPanels(centerPanel, inputs, outputs) {
        const appEl = this.$el
        const spaceEl = document.querySelector('.layer-space') || appEl
        const toolbarEl = document.getElementById('toolbar')
        const spaceRect = spaceEl.getBoundingClientRect()
        const toolbarHeight = toolbarEl?.getBoundingClientRect().height || 0
        const margin = 20
        const sideGap = 48
        const stackGap = 18
        const minTop = toolbarHeight + margin
        const maxHeight = spaceRect.height - margin

        const centerEl = this._getPanelElement(centerPanel)
        if (!centerEl) return

        const centerRect = centerEl.getBoundingClientRect()
        const centerLeft = this._clampFocusLeft((spaceRect.width - centerRect.width) / 2, centerRect.width, spaceRect.width, margin)
        const centerTop = this._clampFocusTop(toolbarHeight + (spaceRect.height - toolbarHeight - centerRect.height) / 2, centerRect.height, minTop, maxHeight)

        this._applyFocusedPosition(centerPanel, centerLeft, centerTop, 'center')

        const inputAnchor = centerLeft - sideGap
        const outputAnchor = centerLeft + centerRect.width + sideGap
        const centerY = centerTop + centerRect.height / 2

        this._layoutFocusColumn(inputs, 'input', {
            centerY,
            anchorX: inputAnchor,
            align: 'right',
            minTop,
            maxHeight,
            maxWidth: spaceRect.width,
            margin,
            stackGap,
        })

        this._layoutFocusColumn(outputs, 'output', {
            centerY,
            anchorX: outputAnchor,
            align: 'left',
            minTop,
            maxHeight,
            maxWidth: spaceRect.width,
            margin,
            stackGap,
        })

        if (typeof dispatchRequestDrawEvent !== 'undefined') {
            dispatchRequestDrawEvent()
        }
    },

    _layoutFocusColumn(panels, role, conf) {
        if (!panels.length) return

        const measured = panels.map(panel => {
            const el = this._getPanelElement(panel)
            const rect = el?.getBoundingClientRect()
            return {
                panel,
                width: rect?.width || el?.offsetWidth || 280,
                height: rect?.height || el?.offsetHeight || 160,
            }
        })

        const totalHeight = measured.reduce((sum, item) => sum + item.height, 0)
            + Math.max(0, measured.length - 1) * conf.stackGap
        let top = conf.centerY - totalHeight / 2

        measured.forEach(item => {
            const rawLeft = conf.align === 'right'
                ? conf.anchorX - item.width
                : conf.anchorX
            const left = this._clampFocusLeft(rawLeft, item.width, conf.maxWidth, conf.margin)
            const clampedTop = this._clampFocusTop(top, item.height, conf.minTop, conf.maxHeight)
            this._applyFocusedPosition(item.panel, left, clampedTop, role)
            top += item.height + conf.stackGap
        })
    },

    _clampFocusLeft(left, width, maxWidth, margin) {
        return Math.min(Math.max(left, margin), maxWidth - width - margin)
    },

    _clampFocusTop(top, height, minTop, maxHeight) {
        return Math.min(Math.max(top, minTop), maxHeight - height)
    },

    _applyFocusedPosition(panel, left, top, role) {
        const el = this._getPanelElement(panel)
        if (!el) return
        panel._focusPinned = true
        panel._focusRole = role
        el.style.left = `${Math.round(left)}px`
        el.style.top = `${Math.round(top)}px`
    },

    _getPanelElement(panel) {
        if (!panel) return null
        const ref = this.$refs[`panel-${panel.id}`]
        return Array.isArray(ref) ? ref[0] : ref
    },
}