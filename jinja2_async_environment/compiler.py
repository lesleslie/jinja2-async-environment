import typing as t

from jinja2 import nodes
from jinja2.compiler import CodeGenerator, CompilerExit, Frame


class AsyncFrame(Frame):
    block_frame: "AsyncFrame | None"
    block_counters: t.Mapping[str, int]
    block_frame_id: int
    require_output_check: bool
    has_known_extends: bool
    toplevel: bool
    rootlevel: bool
    buffer: t.Any | None

    def copy(self) -> t.Self:
        rv = super().copy()
        t.cast(AsyncFrame, rv)
        return rv

    def inspect(self, nodes: t.Any | None = None) -> None: ...

    def push_scope(self) -> None: ...

    def pop_scope(self) -> None: ...

    def find_break(self) -> bool: ...

    def find_continue(self) -> bool: ...


class AsyncCodeGenerator(CodeGenerator):
    environment: t.Any
    name: str
    filename: str
    stream: t.Any
    extends_so_far: int
    has_known_extends: bool

    def visit_Block(self, node: nodes.Block, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        level = 0
        if frame.toplevel:
            if self.has_known_extends:
                return
            if self.extends_so_far > 0:
                self.writeline("if parent_template is None:")
                self.indent()
                level += 1
        if node.scoped:
            context = self.derive_context(frame)
        else:
            context = self.get_context_ref()
        if node.required:
            self.writeline(f"if len(context.blocks[{node.name!r}]) <= 1:", node)
            self.indent()
            self.writeline(
                f'raise TemplateRuntimeError("Required block {node.name!r} not found")',
                node,
            )
            self.outdent()
        if not self.environment.enable_async and frame.buffer is None:
            self.writeline(
                f"yield from context.blocks[{node.name!r}][0]({context})", node
            )
        else:
            self.writeline(
                f"{self.choose_async()}for event in context.blocks[{node.name!r}][0]({context}):",
                node,
            )
            self.indent()
            self.simple_write("event", frame)
            self.outdent()
        self.outdent(level)

    def visit_Extends(self, node: nodes.Extends, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        if not frame.require_output_check:
            raise CompilerExit()
        if not frame.toplevel:
            self.fail("cannot use extend from a non top-level scope", node.lineno)
        if self.extends_so_far > 0:
            if not self.has_known_extends:
                self.writeline("if parent_template is not None:")
                self.indent()
            self.writeline('raise TemplateRuntimeError("extended multiple times")')
            if self.has_known_extends:
                raise CompilerExit()
            else:
                self.outdent()
        self.writeline("parent_template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        self.writeline("for name, parent_block in parent_template.blocks.items():")
        self.indent()
        self.writeline("context.blocks.setdefault(name, []).append(parent_block)")
        self.outdent()
        if frame.rootlevel:
            self.has_known_extends = True
        self.extends_so_far += 1

    def visit_Include(self, node: nodes.Include, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        if node.ignore_missing:
            self.writeline("try:")
            self.indent()
        self.writeline("template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        if node.ignore_missing:
            self.outdent()
            self.writeline("except TemplateNotFound:")
            self.indent()
            self.writeline("pass")
            self.outdent()
            self.writeline("else:")
            self.indent()
        if node.with_context:
            self.writeline(
                f"async for event in template.root_render_func(template.new_context(context.get_all(), True, {self.dump_local_context(frame)})):"
            )
        else:
            self.writeline(
                "async for event in (await template._get_default_module_async())._body_stream:"
            )
        self.indent()
        self.simple_write("event", frame)
        self.outdent()
        if node.ignore_missing:
            self.outdent()

    def _import_common(
        self, node: nodes.Import | nodes.FromImport, frame: Frame
    ) -> None:
        frame = t.cast(AsyncFrame, frame)
        self.writeline("try:")
        self.indent()
        self.writeline("template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        self.outdent()
        self.writeline("except TemplateNotFound:")
        self.indent()
        self.writeline("template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        self.outdent()
