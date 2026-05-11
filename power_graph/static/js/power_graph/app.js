const { createApp } = Vue;

createApp({
  data() {
    return {
    //   wsUrl:           'ws://localhost:8765',
      wsUrl:           'wss://studious-bassoon-9wgj4w4jxcxj7q-8765.app.github.dev/',
      status:          'disconnected',
      panels:          {},      // id → panel object
      selectedPanel:   null,
      selectedFieldKey: null,
      focusedFieldKey:  null,
      fieldEdits:      {},      // key → JSON-string draft

      // command builder
      op:      'toggle',
      opId:    '',
      opKey:   '',
      opValue: '',

      rawCmd:     '{"op":"read_all"}',
      logEntries: [],
      connections: [],    // [{from_id, to_id, …}] — topology
      detailOpen:  false,
    };
  },

  computed: {
    sortedPanels() {
      return Object.values(this.panels).sort((a, b) => a.id - b.id);
    },
    detailFields() {
      if (!this.selectedPanel) return [];
      return Object.entries(this.selectedPanel).map(([k, v]) => ({
        key: k,
        editable: typeof v !== 'object' || v === null,
        raw: JSON.stringify(v),
      }));
    },
  },

  mounted() {
    this._canvas = new ConnectionCanvas();
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') this.closeDetail();
    });
  },

  watch: {
    selectedPanel(p) {
      if (!p) { this._canvas.clear(); return; }
      // Refresh connections on every selection so all edges are guaranteed current
      Vue.nextTick(() => this._fetchAndDraw(p.id));
    },
  },

  methods: {
    // ── Connections ────────────────────────────────────────────────────
    fetchConnections() {
      if (!this._ws || this._ws.readyState !== WebSocket.OPEN) return;
      const loop  = this._ws;  // capture for the one-shot response
      const onMsg = ({ data }) => {
        let msg;
        try { msg = JSON.parse(data); } catch { return; }
        if (msg.type === 'reply' && Array.isArray(msg.connections)) {
          this.connections = msg.connections;
          loop.removeEventListener('message', onMsg);
        }
      };
      loop.addEventListener('message', onMsg);
      this.sendCmd({ op: 'read_connections' });
    },

    _fetchAndDraw(panelId) {
      if (!this._ws || this._ws.readyState !== WebSocket.OPEN) return;
      const loop  = this._ws;
      const onMsg = ({ data }) => {
        let msg;
        try { msg = JSON.parse(data); } catch { return; }
        if (msg.type === 'reply' && Array.isArray(msg.connections)) {
          this.connections = msg.connections;
          loop.removeEventListener('message', onMsg);
          // Draw after the data arrives, ensuring all cards are in the DOM
          Vue.nextTick(() => this._canvas.draw(panelId, this.connections));
        }
      };
      loop.addEventListener('message', onMsg);
      this.sendCmd({ op: 'read_connections' });
    },

    // ── WebSocket ──────────────────────────────────────────────────────
    connect() {
      if (this._ws) this._ws.close();
      this.status = 'connecting';
      const ws = new WebSocket(this.wsUrl);
      this._ws = ws;

      ws.onopen = () => {
        this.status = 'connected';
        this.addLog('info', `connected to ${this.wsUrl}`);
        this.sendCmd({ op: 'read_all' });
        this.fetchConnections();
      };
      ws.onclose = () => {
        this.status = 'disconnected';
        this.addLog('info', 'connection closed');
      };
      ws.onerror = () => {
        this.status = 'disconnected';
        this.addLog('err', 'WebSocket error');
      };
      ws.onmessage = ({ data }) => {
        let msg;
        try { msg = JSON.parse(data); } catch { this.addLog('err', `bad JSON: ${data}`); return; }
        this.handleMessage(msg);
      };
    },

    sendCmd(cmd) {
      if (!this._ws || this._ws.readyState !== WebSocket.OPEN) {
        this.addLog('err', 'not connected'); return;
      }
      const raw = JSON.stringify(cmd);
      this._ws.send(raw);
      this.addLog('out', raw);
    },

    // ── Message handling ───────────────────────────────────────────────
    handleMessage(msg) {
      this.addLog('in', JSON.stringify(msg).slice(0, 300));
      if (msg.type === 'tick' && Array.isArray(msg.panels)) {
        this.ingestPanels(msg.panels);
      } else if (msg.type === 'reply' && Array.isArray(msg.panels)) {
        this.ingestPanels(msg.panels);
      } else if (msg.type === 'reply' && msg.panel) {
        this.ingestPanels([msg.panel]);
        if (this.selectedPanel?.id === msg.panel.id) {
          this.selectedPanel = this.panels[msg.panel.id];
        }
      } else if (msg.type === 'error') {
        this.addLog('err', `server: ${msg.message}`);
      }
    },

    ingestPanels(list) {
      list.forEach(p => { this.panels[p.id] = p; });
      // Refresh detail fields without overwriting focused input
      if (this.selectedPanel) {
        const updated = this.panels[this.selectedPanel.id];
        if (updated) {
          this.selectedPanel = updated;
          Object.entries(updated).forEach(([k, v]) => {
            if (k !== this.focusedFieldKey && (typeof v !== 'object' || v === null)) {
              this.fieldEdits[k] = JSON.stringify(v);
            }
          });
        }
      }
    },

    // ── Panels watt helper ─────────────────────────────────────────────
    panelWatts(p) {
      const w = p.drawWatts ?? p.current_watts ?? p.watts ?? null;
      return w !== null ? `${Number(w).toFixed(0)} W` : '';
    },

    // ── Detail overlay ─────────────────────────────────────────────────
    openDetail(panel) {
      this.selectedPanel   = panel;
      this.detailOpen      = true;
      this.selectedFieldKey = null;
      this.focusedFieldKey  = null;
      this.fieldEdits       = {};
      Object.entries(panel).forEach(([k, v]) => {
        if (typeof v !== 'object' || v === null) this.fieldEdits[k] = JSON.stringify(v);
      });
    },

    selectPanel(panel) {
      this.selectedPanel = (this.selectedPanel?.id === panel.id) ? null : panel;
    },

    closeDetail() {
      this.detailOpen       = false;
      this.selectedFieldKey = null;
    },

    togglePanel() {
      if (!this.selectedPanel) return;
      this.sendCmd({ op: 'toggle', id: this.selectedPanel.id });
      setTimeout(() => this.sendCmd({ op: 'read', id: this.selectedPanel.id }), 120);
    },

    resetPanel() {
      if (!this.selectedPanel) return;
      this.sendCmd({ op: 'reset', id: this.selectedPanel.id });
      setTimeout(() => this.sendCmd({ op: 'read', id: this.selectedPanel.id }), 120);
    },

    cardEnable(p, enabled) {
      p.enabled = enabled;              // optimistic — Vue re-renders immediately
      this.sendCmd({ op: 'set', id: p.id, key: 'enabled', value: enabled });
      this.sendCmd({ op: 'repropagate' });
      setTimeout(() => this.sendCmd({ op: 'read', id: p.id }), 120);
    },

    cardReset(p) {
      this.sendCmd({ op: 'reset', id: p.id });
      setTimeout(() => this.sendCmd({ op: 'read', id: p.id }), 120);
    },

    setField() {
      if (!this.selectedPanel || !this.selectedFieldKey) {
        this.addLog('info', 'click a field input first'); return;
      }
      const raw = this.fieldEdits[this.selectedFieldKey];
      let value;
      try { value = JSON.parse(raw); }
      catch { this.addLog('err', `invalid JSON: ${raw}`); return; }
      this.sendCmd({ op: 'set', id: this.selectedPanel.id, key: this.selectedFieldKey, value });
      setTimeout(() => this.sendCmd({ op: 'read', id: this.selectedPanel.id }), 120);
    },

    // ── Command builder ────────────────────────────────────────────────
    sendBuilder() {
      const id  = parseInt(this.opId, 10);
      const cmd = { op: this.op };
      if (!isNaN(id)) cmd.id = id;
      if (this.op === 'set') {
        cmd.key = this.opKey.trim();
        try { cmd.value = JSON.parse(this.opValue); }
        catch { this.addLog('err', 'value must be valid JSON'); return; }
      }
      this.sendCmd(cmd);
      if (this.op !== 'read' && !isNaN(id)) {
        setTimeout(() => this.sendCmd({ op: 'read', id }), 120);
      }
    },

    // ── Raw JSON ───────────────────────────────────────────────────────
    sendRaw() {
      let cmd;
      try { cmd = JSON.parse(this.rawCmd); }
      catch { this.addLog('err', `invalid JSON: ${this.rawCmd}`); return; }
      this.sendCmd(cmd);
    },

    // ── Log ────────────────────────────────────────────────────────────
    addLog(type, text) {
      const ts = new Date().toISOString().slice(11, 23);
      this.logEntries.unshift({ type, text: `${ts}  ${text}` });
      if (this.logEntries.length > 200) this.logEntries.length = 200;
    },
    clearLog() { this.logEntries = []; },
  },
}).mount('#app');
