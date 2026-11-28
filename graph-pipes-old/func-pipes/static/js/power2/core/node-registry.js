/*
  core/node-registry.js
  ─────────────────────────────────────────────────────────────────────────────
  NodeRegistry — maps type-string keys to NodeBase sub-classes.

  Each node file calls NodeRegistry.register(MyClass) at the bottom, making
  itself visible to the Graph engine. Nodes are loaded at will by including
  their <script> tag in the HTML — the registry handles the rest.

  API
  ───
  NodeRegistry.register(NodeClass)          — register a node type
  NodeRegistry.get(type)  → NodeBase|null  — retrieve class by type key
  NodeRegistry.create(type, id, preset)     — factory: call class.defaults()
  NodeRegistry.catalog()  → Array           — all catalog entries (all types)
  NodeRegistry.catalogByGroup() → Object    — catalog grouped by group string
  NodeRegistry.allTypes() → string[]        — list of registered type keys
*/

const NodeRegistry = (() => {

    const _registry = new Map()   // type key → NodeBase sub-class

    // ── Public API ──────────────────────────────────────────────────────────

    /**
     * Register a node class. Called automatically at end of each node file.
     * @param {typeof NodeBase} NodeClass
     */
    function register(NodeClass) {
        if (!NodeClass.type || NodeClass.type === 'base') {
            console.warn('[NodeRegistry] Cannot register class without a type:', NodeClass)
            return
        }
        _registry.set(NodeClass.type, NodeClass)
    }

    /**
     * Retrieve the class for a type key.
     * @param  {string} type
     * @returns {typeof NodeBase | null}
     */
    function get(type) {
        return _registry.get(type) || null
    }

    /**
     * Create a fresh panel state object for the given type.
     * Wraps the class's defaults() factory so the Graph doesn't import classes directly.
     *
     * @param  {string} type
     * @param  {number} id
     * @param  {Object} preset
     * @returns {Object}  raw panel data (not yet assigned an id — Graph.spawn does that)
     */
    function create(type, id, preset = {}) {
        const Cls = get(type)
        if (!Cls) {
            console.error('[NodeRegistry] Unknown type:', type)
            return null
        }
        return Cls.defaults(id, preset)
    }

    /**
     * Flat list of all catalog entries from every registered node type.
     * Each entry includes a `type` field so callers can create the right node.
     * @returns {Array}
     */
    function catalog() {
        const result = []
        _registry.forEach((Cls) => {
            Cls.catalog.forEach(entry => {
                result.push({ ...entry, type: Cls.type, group: entry.group || Cls.group })
            })
        })
        return result
    }

    /**
     * The catalog grouped by group string.
     * @returns {{ [group: string]: Array }}
     */
    function catalogByGroup() {
        const groups = {}
        catalog().forEach(entry => {
            const g = entry.group || 'Other'
            if (!groups[g]) groups[g] = []
            groups[g].push(entry)
        })
        return groups
    }

    /**
     * All registered type keys.
     * @returns {string[]}
     */
    function allTypes() {
        return [..._registry.keys()]
    }

    return { register, get, create, catalog, catalogByGroup, allTypes }

})()
