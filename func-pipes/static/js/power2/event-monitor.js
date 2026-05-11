/*
  power2/event-monitor.js — Centralised Event Monitor Vue App
  ────────────────────────────────────────────────────────────
  Mounts a separate Vue app on #event-monitor.
  Listens for any CustomEvent dispatched on window with category "power2".
  Publish events from anywhere:

      window.dispatchEvent(new CustomEvent('power2', {
          detail: { type: 'node:tick', label: 'gen-1', data: { v: 12 } }
      }))

  Events are prepended (newest first) and capped at MAX_EVENTS.
*/

const MAX_EVENTS = 1000

createApp({
    data() {
        return {
            events:          [],
            visible:         true,
            _counter:        0,
            eventsPerSecond: 0,
            _epsAccum:       0,
            kbPerSecond:     0,
            _kbAccum:        0,
            _epsInterval:    null,
        }
    },

    mounted() {
        this._handler = e => this.push(e.detail)
        window.addEventListener('power2', this._handler)
        this._epsInterval = setInterval(() => {
            this.eventsPerSecond = this._epsAccum
            this._epsAccum = 0
            this.kbPerSecond = (this._kbAccum / 1024).toFixed(2)
            this._kbAccum = 0
        }, 1000)
        this.push({ type: 'monitor:ready', label: 'event-monitor', data: { max: MAX_EVENTS } })
    },

    beforeUnmount() {
        window.removeEventListener('power2', this._handler)
        clearInterval(this._epsInterval)
    },

    methods: {
        push(detail = {}) {
            this._epsAccum++
            const serialised = JSON.stringify(detail)
            this._kbAccum += new Blob([serialised]).size
            this.events.unshift({
                id:    ++this._counter,
                ts:    new Date().toISOString().slice(11, 23),
                type:  detail.type  || 'event',
                label: detail.label || '',
                data:  detail.data != null ? JSON.stringify(detail.data) : '',
            })
            if (this.events.length > MAX_EVENTS) this.events.length = MAX_EVENTS
        },

        clear() { this.events = [] },
    },

    template: '#em-template',
}).mount('#event-monitor')
