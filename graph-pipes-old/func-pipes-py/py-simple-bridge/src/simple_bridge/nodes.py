from __future__ import annotations

import inspect
from typing import Any, Callable


def node_passthrough(in_value: Any) -> Any:
    """Return the input value unchanged.

    Description:
        Provide the smallest possible node function for tests and examples.

    Example:
        node_passthrough("seed")

    Expected output:
        Returns `"seed"`.

    Caveats:
        The function does not inspect or alter pip names.
    """
    return in_value


def node_multiply(in_value: Any, multiplier: int | float = 2) -> Any:
    """Multiply one numeric input by a fixed factor.

    Description:
        Offer a simple pure function for demonstrations where one node changes
        a value before passing it downstream.

    Example:
        node_multiply(3, multiplier=4)

    Expected output:
        Returns `12`.

    Caveats:
        The input must support the `*` operator with the supplied multiplier.
    """
    return in_value * multiplier


class FunctionNode:
    """Adapt a plain function to the bridge node contract.

    Description:
        Wrap a regular function so it can be registered as a bridge node with a
        stable `node_id` and async-compatible execution method.

    Example:
        node = FunctionNode("mult", node_multiply)

    Expected output:
        `node` can be registered with `SimpleBridge.register_node(node)`.

    Caveats:
        This adapter ignores the inbound pip name; use a custom node class when
        the pip name matters.
    """

    def __init__(self, node_id: str, func: Callable[[Any], Any]) -> None:
        """Store the node id and wrapped function.

        Description:
            Save the identifier used by the bridge registry and the callable
            that should run when the node is invoked.

        Example:
            node = FunctionNode("echo", node_passthrough)

        Expected output:
            `node.node_id` is `"echo"` and `node.func` points to the supplied
            function.

        Caveats:
            Registering another node with the same id later will replace it in
            the bridge.
        """
        self.node_id = node_id
        self.func = func

    async def graph_execute(self, value: Any, pip: str = "in") -> Any:
        """Run the wrapped function for one bridge call.

        Description:
            Forward the input value to the wrapped callable and await it if it
            returns an awaitable object.

        Example:
            node = FunctionNode("echo", node_passthrough)
            result = await node.graph_execute("seed", pip="foo")

        Expected output:
            `result` matches the wrapped function output.

        Caveats:
            The `pip` argument is ignored by this adapter.
        """
        del pip
        result = self.func(value)
        if inspect.isawaitable(result):
            return await result
        return result
