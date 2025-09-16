"""Async frame implementation for template compilation."""

import typing as t

from jinja2.compiler import Frame
from jinja2.nodes import EvalContext

if t.TYPE_CHECKING:
    pass


class AsyncFrame(Frame):
    """Async-aware frame for template compilation context."""

    block_frame: bool  # Keep consistent with base class
    block_frame_ref: "AsyncFrame | None"  # New attribute for async frame reference
    require_output_check: bool
    has_known_extends: bool
    toplevel: bool
    rootlevel: bool
    buffer: str | None
    block_buffer: list[str]
    extended_buffer: list[str] | None
    require_yield: bool
    buffer_count: int
    is_async: bool

    def __init__(self, eval_ctx: EvalContext | None = None) -> None:
        if eval_ctx is None:
            from jinja2.environment import Environment
            from jinja2.nodes import EvalContext

            eval_ctx = EvalContext(Environment(autoescape=True), "template")

        super().__init__(eval_ctx)
        self.buffer = None
        self.block_buffer = []
        self.extended_buffer = None
        self.block_frame = False
        self.block_frame_ref = None
        self.require_output_check = False
        self.has_known_extends = False
        self.toplevel = False
        self.rootlevel = False
        self.require_yield = False
        self.buffer_count = 0
        self.is_async = False
        self.block_counters: dict[str, int] = {}
        self.block_frame_id = 0

    def copy(self) -> t.Self:
        """Create a copy of this frame."""
        rv = self.__class__(self.eval_ctx)
        rv.symbols = self.symbols.copy()  # noqa: FURB145
        rv.buffer = self.buffer
        rv.block_buffer = self.block_buffer
        rv.extended_buffer = self.extended_buffer
        rv.eval_ctx = self.eval_ctx
        rv.parent = self
        rv.require_output_check = self.require_output_check
        rv.has_known_extends = self.has_known_extends
        rv.toplevel = self.toplevel
        rv.rootlevel = self.rootlevel
        rv.block_frame = self.block_frame
        rv.block_frame_ref = self.block_frame_ref
        rv.require_yield = self.require_yield
        rv.buffer_count = self.buffer_count
        rv.is_async = self.is_async
        rv.block_counters = self.block_counters.copy()  # noqa: FURB145
        rv.block_frame_id = self.block_frame_id
        return rv

    def inspect(self, nodes: t.Any | None = None) -> None:
        """Inspect nodes for symbol analysis."""
        if nodes:
            for node in nodes:
                self.symbols.analyze_node(node)

    def push_scope(self) -> None:
        """Push a new scope (no-op for async frame)."""
        pass

    def pop_scope(self) -> None:
        """Pop the current scope (no-op for async frame)."""
        pass

    def find_break(self) -> bool:
        """Check if break statement is valid (always False)."""
        return False

    def find_continue(self) -> bool:
        """Check if continue statement is valid (always False)."""
        return False

    def inner(self, isolated: bool = False) -> "AsyncFrame":
        """Create an inner frame."""
        return self.copy()
