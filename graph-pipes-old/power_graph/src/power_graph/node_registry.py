"""
node_registry.py
──────────────────────────────────────────────────────────────────────────────
NodeRegistry — maps type-string keys to NodeBase subclasses.

Each node class registers itself via NodeRegistry.register(NodeClass) at
module load time, making it available to the graph engine.

API:
  NodeRegistry.register(NodeClass)         — register a node type
  NodeRegistry.get(type)                   — retrieve class by type key
  NodeRegistry.create(type, id, preset)    — factory: call class.defaults()
  NodeRegistry.catalog()                   — all catalog entries (all types)
  NodeRegistry.catalog_by_group()          — catalog grouped by group string
  NodeRegistry.all_types()                 — list of registered type keys
"""

from typing import Dict, Type, List, Any, Optional


class _NodeRegistrySingleton:
    """Registry singleton — maps type keys to NodeBase subclasses."""

    def __init__(self):
        self._registry: Dict[str, Type] = {}

    def register(self, node_class: Type):
        """
        Register a node class.

        Args:
            node_class: NodeBase subclass with a 'type' attribute

        Raises:
            ValueError: If class has no type or type is 'base'
        """
        if not hasattr(node_class, 'type'):
            raise ValueError(f"Node class {node_class} has no 'type' attribute")

        node_type = node_class.type
        if node_type == 'base' or not node_type:
            raise ValueError(f"Cannot register class with type '{node_type}'")

        self._registry[node_type] = node_class
        print(f"[NodeRegistry] Registered {node_type} → {node_class.__name__}")

    def get(self, node_type: str) -> Optional[Type]:
        """
        Retrieve the class for a type key.

        Args:
            node_type: Type string (e.g. 'gen', 'bulb', 'load')

        Returns:
            NodeBase subclass or None if not found
        """
        return self._registry.get(node_type)

    def create(self, node_type: str, node_id: int, preset: Dict = None) -> Optional[Dict]:
        """
        Create a fresh panel state object for the given type.

        Wraps the class's defaults() factory so the graph doesn't need to
        import individual node classes directly.

        Args:
            node_type: Type string
            node_id: Unique panel ID
            preset: Configuration preset dict

        Returns:
            Raw panel data dict or None if type not found
        """
        if preset is None:
            preset = {}

        node_cls = self.get(node_type)
        if not node_cls:
            raise ValueError(f"Unknown node type: {node_type}")

        if not hasattr(node_cls, 'defaults'):
            raise ValueError(f"Node class {node_cls} has no 'defaults()' method")

        return node_cls.defaults(node_id, preset)

    def catalog(self) -> List[Dict[str, Any]]:
        """
        Get flat list of all catalog entries from every registered type.

        Each entry includes a 'type' field for creating nodes.

        Returns:
            List of catalog entry dicts
        """
        result = []
        for node_cls in self._registry.values():
            if hasattr(node_cls, 'catalog'):
                for entry in node_cls.catalog:
                    entry_copy = dict(entry)
                    entry_copy['type'] = node_cls.type
                    if 'group' not in entry_copy and hasattr(node_cls, 'group'):
                        entry_copy['group'] = node_cls.group
                    result.append(entry_copy)
        return result

    def catalog_by_group(self) -> Dict[str, List[Dict]]:
        """
        Get catalog entries grouped by group string.

        Returns:
            Dict mapping group name → list of catalog entries
        """
        groups = {}
        for entry in self.catalog():
            group = entry.get('group', 'Other')
            if group not in groups:
                groups[group] = []
            groups[group].append(entry)
        return groups

    def all_types(self) -> List[str]:
        """
        Get all registered type keys.

        Returns:
            List of type strings
        """
        return list(self._registry.keys())

    def all_classes(self) -> Dict[str, Type]:
        """Get all registered type → class mappings."""
        return dict(self._registry)

    def unregister(self, node_type: str):
        """Unregister a node type (mainly for testing)."""
        if node_type in self._registry:
            del self._registry[node_type]

    def clear(self):
        """Clear all registrations (mainly for testing)."""
        self._registry.clear()


# Global singleton instance
NodeRegistry = _NodeRegistrySingleton()
