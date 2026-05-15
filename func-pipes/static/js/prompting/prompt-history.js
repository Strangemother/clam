/*
  prompt-history.js
  ─────────────────────────────────────────────────────────────────────────────
  Runtime-only per-panel input history for manual entry fields.

  History is isolated from message replay and layout persistence.
  Each panel keeps independent field histories capped to the most recent items.
*/

const PANEL_INPUT_HISTORY_LIMIT = 20

const InputHistoryMethods = {

    _getPanelInputHistoryStore(panel) {
        if (!panel._inputHistory) {
            panel._inputHistory = Object.create(null)
        }
        return panel._inputHistory
    },

    _getPanelInputHistoryEntry(panel, fieldKey) {
        const store = this._getPanelInputHistoryStore(panel)
        if (!store[fieldKey]) {
            store[fieldKey] = { items: [], cursor: -1, draft: '' }
        }
        return store[fieldKey]
    },

    _getPanelInputHistoryValue(panel, fieldKey) {
        if (fieldKey.startsWith('values:')) {
            const key = fieldKey.slice('values:'.length)
            return panel.values?.[key] ?? ''
        }
        return panel[fieldKey] ?? ''
    },

    _setPanelInputHistoryValue(panel, fieldKey, value) {
        if (fieldKey.startsWith('values:')) {
            const key = fieldKey.slice('values:'.length)
            if (!panel.values) panel.values = {}
            panel.values[key] = value
            return
        }
        panel[fieldKey] = value
    },

    rememberPanelInput(panel, fieldKey, value) {
        const text = value == null ? '' : String(value)
        const trimmed = text.trim()
        const entry = this._getPanelInputHistoryEntry(panel, fieldKey)

        if (!trimmed) {
            entry.cursor = -1
            entry.draft = ''
            return
        }

        if (entry.items[entry.items.length - 1] !== text) {
            entry.items.push(text)
        }

        if (entry.items.length > PANEL_INPUT_HISTORY_LIMIT) {
            entry.items.splice(0, entry.items.length - PANEL_INPUT_HISTORY_LIMIT)
        }

        entry.cursor = -1
        entry.draft = ''
    },

    touchPanelInputHistory(panel, fieldKey) {
        const entry = this._getPanelInputHistoryEntry(panel, fieldKey)
        entry.cursor = -1
        entry.draft = ''
    },

    resetPanelInputHistoryNavigation(panel, fieldKey = null) {
        const store = panel?._inputHistory
        if (!store) return

        const keys = fieldKey ? [fieldKey] : Object.keys(store)
        keys.forEach(key => {
            if (!store[key]) return
            store[key].cursor = -1
            store[key].draft = ''
        })
    },

    handlePanelInputHistoryKeydown(panel, fieldKey, event) {
        if (!event || (event.key !== 'ArrowUp' && event.key !== 'ArrowDown')) return
        if (!this._shouldHandlePanelInputHistoryKey(event)) return

        const nextValue = this._stepPanelInputHistory(
            panel,
            fieldKey,
            event.key === 'ArrowUp' ? -1 : 1,
        )
        if (nextValue === null) return

        event.preventDefault()
        this._setPanelInputHistoryValue(panel, fieldKey, nextValue)

        nextTick(() => {
            const target = event.target
            if (!target || typeof target.setSelectionRange !== 'function') return
            const length = String(nextValue).length
            target.setSelectionRange(length, length)
        })
    },

    _shouldHandlePanelInputHistoryKey(event) {
        if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.isComposing) {
            return false
        }

        const target = event.target
        if (!target) return true

        const inputType = String(target.type || '').toLowerCase()
        if (inputType === 'number') return false

        if (target.tagName !== 'TEXTAREA') return true

        const start = target.selectionStart ?? 0
        const end = target.selectionEnd ?? 0
        if (start !== end) return false

        const value = String(target.value || '')
        if (event.key === 'ArrowUp') {
            return !value.slice(0, start).includes('\n')
        }
        if (event.key === 'ArrowDown') {
            return !value.slice(start).includes('\n')
        }
        return false
    },

    _stepPanelInputHistory(panel, fieldKey, direction) {
        const entry = this._getPanelInputHistoryEntry(panel, fieldKey)
        if (!entry.items.length) return null

        const currentValue = String(this._getPanelInputHistoryValue(panel, fieldKey) ?? '')

        if (direction < 0) {
            if (entry.cursor === -1) {
                entry.draft = currentValue
                entry.cursor = entry.items.length - 1
            } else if (entry.cursor > 0) {
                entry.cursor -= 1
            }
            return entry.items[entry.cursor] ?? null
        }

        if (entry.cursor === -1) return null

        if (entry.cursor < entry.items.length - 1) {
            entry.cursor += 1
            return entry.items[entry.cursor] ?? null
        }

        entry.cursor = -1
        const draft = entry.draft
        entry.draft = ''
        return draft
    },
}