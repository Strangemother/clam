
const LogicNode = Object.assign({}, NodeBase, {
    // props: ['uuid', 'panel']
    template: getTemplateHTML('.logic-node')
    , data() {
        return {
            selectedGate: 'or'
        }
    }

    , mounted() {
        // super.mounted()
        this.panel._viewComponent = this

        this.panel.pipsInbound = [{
                    name: 'a'
                }, {
                    name: 'b'
                }]

    }

    , methods: Object.assign({}, PanelBaseMethods, {
        sendContent() {
            console.log('sendContent', this.userText)
            this.saveSend(this.userText)
        }

        , saveSend(text, inputPip='out') {
            // this.items.push({ pip: inputPip, value: text })
            this.panel.viewData.value = text
            simpleBridge.emitResultThrough(text, {
                id: this.panel.id,
                pip: inputPip // currently ignored
            })
        }

        , reflowSelection() {
            console.log('reflowSelection')
            this.saveSend(this.customCallback())
        }

        , customCallback(data, pip) {
            // somehow called be the spawnpanel callback.
            console.log('customCallback', data, pip)

            let func = this.selectedGate || 'and'

            let a = this.panel.pipData.a
            let b = this.panel.pipData.b
            let res = this[func](a, b)
            console.log('res', a,b, res)
            return res;
        }

        /* ── helpers ────────────────────────────────────────────────────── */
        , _bool(v) {
            return v === '1' || v === 1 || v === true || v === 'true' || v === 'HIGH'
        }

        , _bit(v) { return v ? 1 : 0 }

        /* ── gates ──────────────────────────────────────────────────────── */

        , buffer(input) {
            return this._bit(this._bool(input))
        }
        , not(a) {
            return this._bit(!this._bool(a))
        }

        , and(a, b) {
            return this._bit(this._bool(a) && this._bool(b))
        }
        , or(a, b) {
            return this._bit(this._bool(a) || this._bool(b))
        }
        , nand(a, b) {
            return this._bit(!(this._bool(a) && this._bool(b)))
        }
        , nor(a, b) {
            return this._bit(!(this._bool(a) || this._bool(b)))
        }
        , xor(a, b) {
            return this._bit(this._bool(a) !== this._bool(b))
        }
        , xnor(a, b) {
            return this._bit(this._bool(a) === this._bool(b))
        }

    })
});

nodeRegister.LogicNode = LogicNode


