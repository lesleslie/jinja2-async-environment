import typing as t

from jinja2 import nodes
from jinja2.compiler import CodeGenerator, CompilerExit, EvalContext, Frame
from markupsafe import escape


class AsyncFrame(Frame):
    block_frame: "AsyncFrame | None"
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
        self.block_frame = None
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
        rv.require_yield = self.require_yield
        rv.buffer_count = self.buffer_count
        rv.is_async = self.is_async
        rv.block_counters = self.block_counters.copy()  # noqa: FURB145
        rv.block_frame_id = self.block_frame_id
        return rv

    def inspect(self, nodes: t.Any | None = None) -> None:
        if nodes:
            for node in nodes:
                self.symbols.analyze_node(node)

    def push_scope(self) -> None:
        pass

    def pop_scope(self) -> None:
        pass

    def find_break(self) -> bool:
        return False

    def find_continue(self) -> bool:
        return False


class AsyncCodeGenerator(CodeGenerator):
    environment: t.Any
    name: str
    filename: str
    stream: t.Any
    extends_so_far: int
    has_known_extends: bool
    root_frame_class: type[AsyncFrame] = AsyncFrame
    eval_ctx: t.Any = None
    is_async: bool = True
    last_identifier: int = 0
    identifiers: dict[str, t.Any] = {}
    import_aliases: dict[str, t.Any] = {}
    blocks: dict[str, t.Any] = {}
    extends_buffer: t.Any = None
    required_blocks: set[str] = set()
    has_super: bool = False
    macro_frames: list[AsyncFrame] = []

    def __init__(
        self, environment: t.Any, name: str, filename: str, defer_init: bool = False
    ) -> None:
        super().__init__(
            environment, name, filename, stream=None, defer_init=defer_init
        )
        self.extends_so_far = 0
        self.has_known_extends = False
        self.has_super = False
        self.last_identifier = 0
        self.identifiers = {}
        self.import_aliases = {}
        self.blocks = {}
        self.extends_buffer = None
        self.required_blocks = set()
        self.is_async = True
        self.macro_frames = []

        from jinja2.defaults import DEFAULT_FILTERS

        self.filters.update(t.cast(dict[str, str], DEFAULT_FILTERS))
        self.filters["escape"] = escape.__name__

        from jinja2.nodes import EvalContext

        if self.eval_ctx is None:
            self.eval_ctx = EvalContext(self.environment, self.name)

    def choose_async(self) -> str:  # type: ignore[override]
        return "async " if self.environment.enable_async else ""

    def simple_write(self, value: str, frame: Frame) -> None:  # type: ignore[override]
        self.writeline(f"yield {value}")

    def func_code_generator(self, frame: Frame) -> str:
        async_frame = t.cast(AsyncFrame, frame)
        return "async def" if async_frame.is_async else "def"

    def return_buffer_contents(
        self,
        frame: Frame,
        force_unescaped: bool = False,  # noqa: ARG002
    ) -> None:
        _ = force_unescaped
        if frame.buffer is not None:
            self.writeline(f"return ''.join({frame.buffer})")

    def visit_AsyncFor(self, node: t.Any, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        if hasattr(node, "recursive") and node.recursive:
            raise NotImplementedError("Recursive loops not supported")
        target = node.target
        item = target.name if hasattr(target, "name") else "item"
        frame.symbols.store(item)
        self.writeline(f"{item} = None")
        loop_filter = None
        if hasattr(node, "test") and node.test:
            loop_filter = self.temporary_identifier()
            self.writeline(f"{loop_filter} = ", node.test)
            self.visit(node.test, frame)
        loop_var = self.temporary_identifier()
        self.writeline(f"{loop_var} = -1", node)
        self.writeline(f"async for {item} in ", node.iter)
        self.visit(node.iter, frame)
        self.write(":")
        self.indent()
        self.writeline(f"{loop_var} += 1")
        if hasattr(node, "test") and node.test and loop_filter:
            self.writeline(f"if {loop_filter}({item}):")
            self.indent()
        if hasattr(node, "body"):
            self.blockvisit(node.body, frame)
        if hasattr(node, "test") and node.test and loop_filter:
            self.outdent()
        self.outdent()
        if hasattr(node, "else_") and node.else_:
            self.writeline(f"if {loop_var} == -1:")
            self.indent()
            self.blockvisit(node.else_, frame)
            self.outdent()

    def visit_AsyncCall(self, node: t.Any, frame: Frame) -> None:
        self.write("await ")
        self.visit_Call(node, frame)

    def visit_AsyncFilterBlock(self, node: t.Any, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        if not hasattr(node, "filter"):
            return
        if not hasattr(node, "body"):
            return
        filter_node = node.filter
        buffer = self.temporary_identifier()
        self.writeline(f"{buffer} = []")
        asyncframe = frame.copy()  # noqa: FURB145
        asyncframe.buffer = buffer
        asyncframe.toplevel = False
        self.blockvisit(node.body, asyncframe)
        self.writeline("await ", filter_node)
        self.visit(filter_node, frame)
        self.write(f"(''.join({buffer}))")

    def visit_AsyncBlock(self, node: t.Any, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        if not hasattr(node, "name"):
            return
        if not hasattr(node, "body"):
            return
        block_name = node.name
        self.writeline(f"blocks[{block_name!r}] = []")
        block_func_name = f"block_{block_name}"
        self.writeline(f"async def {block_func_name}(context):")
        self.indent()
        self.writeline("yield ''")
        if node.body:
            self.blockvisit(node.body, frame)
        self.outdent()
        self.writeline(f"blocks[{block_name!r}].append({block_func_name})")

    def visit_Name(self, node: nodes.Name, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        self._handle_assignment_tracking(node, frame)
        if self._handle_special_names(node):
            return
        self._handle_symbol_name(node, frame)

    def _handle_assignment_tracking(self, node: nodes.Name, frame: AsyncFrame) -> None:
        if node.ctx == "store" and (
            frame.toplevel or frame.loop_frame or frame.block_frame
        ):
            if hasattr(self, "_assign_stack") and self._assign_stack:
                self._assign_stack[-1].add(node.name)

    def _handle_special_names(self, node: nodes.Name) -> bool:
        if node.name in ("blocks", "debug_info"):
            self.write(node.name)
            return True
        return False

    def _handle_symbol_name(self, node: nodes.Name, frame: AsyncFrame) -> None:
        try:
            ref = frame.symbols.ref(node.name)
            if node.ctx == "load" and self._should_use_undefined_check(ref, frame):
                self.write(
                    f"(undefined(name={node.name!r}) if {ref} is missing else {ref})"
                )
            else:
                self.write(ref)
        except AssertionError:
            if node.ctx == "load":
                self.write(f"context.get({node.name!r})")
            else:
                self.write(f"context.vars[{node.name!r}]")

    def _should_use_undefined_check(self, ref: str, frame: AsyncFrame) -> bool:
        from jinja2.compiler import VAR_LOAD_PARAMETER

        load = frame.symbols.find_load(ref)
        return not (
            load is not None
            and load[0] == VAR_LOAD_PARAMETER
            and hasattr(self, "parameter_is_undeclared")
            and not self.parameter_is_undeclared(ref)
        )

    def generate(self, node: nodes.Template) -> str:
        self.writeline(f"name = {self.name!r}")
        self.writeline("blocks = {}")
        self.writeline("debug_info = None")
        self.writeline("from jinja2.runtime import Undefined")
        self.writeline("from jinja2.runtime import Macro")
        self.writeline("from jinja2.runtime import missing")
        self.writeline("from markupsafe import escape")
        self.writeline("from jinja2.defaults import DEFAULT_FILTERS")
        self.writeline("def undefined(name=None, **_):")
        self.indent()
        self.writeline("return Undefined(name=name)")
        self.outdent()
        self.writeline("async def auto_await(value):")
        self.indent()
        self.writeline("if hasattr(value, '__await__'):")
        self.indent()
        self.writeline("return await value")
        self.outdent()
        self.writeline("return value")
        self.outdent()
        self.writeline("filters = DEFAULT_FILTERS.copy()")
        self.writeline("filters['escape'] = escape")
        self.writeline("async def root(context):")
        self.indent()
        self.writeline("parent_template = None")
        self.writeline("environment = context.environment")
        self.writeline("eval_ctx = context.eval_ctx")
        self.writeline("undefined = environment.undefined")
        from jinja2.nodes import EvalContext

        if self.eval_ctx is None:
            self.eval_ctx = EvalContext(self.environment, self.name)
        frame = self.root_frame_class(eval_ctx=self.eval_ctx)
        frame.toplevel = frame.rootlevel = True
        frame.require_output_check = False
        frame.buffer = None
        for macro in node.find_all(nodes.Macro):
            frame.symbols.store(macro.name)
        self.blockvisit(node.body, frame)
        self.outdent()

        return self.stream.getvalue()

    def visit_For(self, node: nodes.For, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        node.iter_child_nodes(exclude=("iter",))
        if node.recursive:
            raise NotImplementedError("Recursive loops not supported")
        target = t.cast(t.Any, node.target)
        item_name = target.name
        frame.symbols.store(item_name)
        item_ref = frame.symbols.ref(item_name)
        self.writeline(f"{item_ref} = None")
        loop_filter = self._setup_loop_filter(node, frame)
        loop_var = self.temporary_identifier()
        self.writeline(f"{loop_var} = -1", node)
        self._write_async_for_loop(node, frame, item_ref, loop_var, loop_filter)
        self._write_sync_for_fallback(node, frame, item_ref, loop_var, loop_filter)
        self._write_else_clause(node, frame, loop_var)

    def _setup_loop_filter(self, node: nodes.For, frame: AsyncFrame) -> str | None:
        loop_filter = None
        if node.test:
            loop_filter = self.temporary_identifier()
            self.writeline(f"{loop_filter} = ", node.test)
            self.visit(node.test, frame)
        return loop_filter

    def _write_async_for_loop(
        self,
        node: nodes.For,
        frame: AsyncFrame,
        item_ref: str,
        loop_var: str,
        loop_filter: str | None,
    ) -> None:
        self.writeline("try:", node)
        self.indent()
        self.writeline(f"async for {item_ref} in ", node.iter)
        self.visit(node.iter, frame)
        self.write(":")
        self.indent()
        self.writeline(f"{loop_var} += 1")
        self._write_loop_body_with_filter(node, frame, item_ref, loop_filter)
        self.outdent()
        self.outdent()

    def _write_sync_for_fallback(
        self,
        node: nodes.For,
        frame: AsyncFrame,
        item_ref: str,
        loop_var: str,
        loop_filter: str | None,
    ) -> None:
        self.writeline("except TypeError:", node)
        self.indent()
        self.writeline(f"for {item_ref} in ", node.iter)
        self.visit(node.iter, frame)
        self.write(":")
        self.indent()
        self.writeline(f"{loop_var} += 1")
        self._write_loop_body_with_filter(node, frame, item_ref, loop_filter)
        self.outdent()
        self.outdent()

    def _write_loop_body_with_filter(
        self, node: nodes.For, frame: AsyncFrame, item_ref: str, loop_filter: str | None
    ) -> None:
        if node.test and loop_filter:
            self.writeline(f"if {loop_filter}({item_ref}):")
            self.indent()
        self.blockvisit(node.body, frame)
        if node.test and loop_filter:
            self.outdent()

    def _write_else_clause(
        self, node: nodes.For, frame: AsyncFrame, loop_var: str
    ) -> None:
        if node.else_:
            self.writeline(f"if {loop_var} == -1:")
            self.indent()
            self.blockvisit(node.else_, frame)
            self.outdent()

    def visit_Block(self, node: nodes.Block, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        block_name = node.name
        self.writeline(f"blocks[{block_name!r}] = []")
        block_func_name = f"block_{block_name}"
        self.writeline(f"{self.choose_async()}def {block_func_name}(context):")
        self.indent()
        self.writeline("yield ''")
        if node.body:
            self.blockvisit(node.body, frame)
        self.outdent()
        self.writeline(f"blocks[{block_name!r}].append({block_func_name})")
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
        self.writeline("try:", node)
        self.indent()
        self.writeline(
            f"async for event in context.blocks[{node.name!r}][0]({context}):",
            node,
        )
        self.indent()
        self.simple_write("event", frame)
        self.outdent()
        self.outdent()
        self.writeline("except KeyError:", node)
        self.indent()
        self.writeline("yield ''")
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
        self.writeline("template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
