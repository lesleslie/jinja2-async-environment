"""Loop code generation utilities for for-loops."""

import typing as t

from jinja2 import nodes

if t.TYPE_CHECKING:
    from .codegen import AsyncCodeGenerator
    from .frame import AsyncFrame


class LoopCodeGenerator:
    """Utility class for generating for-loop specific code patterns."""

    def __init__(self, code_generator: "AsyncCodeGenerator") -> None:
        self.code_generator = code_generator

    def generate_async_for_header(
        self, node: nodes.For, target: nodes.Node, frame: "AsyncFrame"
    ) -> None:
        """Generate the async for loop header with proper syntax."""
        self.code_generator.writeline(
            self.code_generator.choose_async("async for ", "for "), node
        )
        self.code_generator.visit(target, frame)

    def generate_loop_iterator(
        self,
        iter_node: nodes.Node,
        frame: "AsyncFrame",
        extended_loop: bool,
        loop_ref: str | None,
        loop_filter_func: str | None,
    ) -> None:
        """Generate the iterator part of the for loop."""
        if extended_loop and loop_ref:
            self.code_generator.write(
                f", {loop_ref} in {self.code_generator.choose_async('Async')}LoopContext("
            )
        else:
            self.code_generator.write(" in ")

        if loop_filter_func:
            self.code_generator.write(f"{loop_filter_func}(")

        if self.code_generator.environment.is_async and not extended_loop:
            self.code_generator.write("auto_aiter(")

        self.code_generator.visit(iter_node, frame)

        if self.code_generator.environment.is_async and not extended_loop:
            self.code_generator.write(")")

        if loop_filter_func:
            self.code_generator.write(")")

        if extended_loop:
            self.code_generator.write(", undefined):")
        else:
            self.code_generator.write(":")
