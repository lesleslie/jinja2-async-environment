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
    root_frame_class: t.Type[AsyncFrame] = AsyncFrame
    eval_ctx: t.Any = None

    def choose_async(self) -> str:  # type: ignore[override]
        return "async " if self.environment.enable_async else ""

    def simple_write(self, value: str, frame: Frame) -> None:  # type: ignore[override]
        self.writeline(f"yield {value}")

    def pull_locals(self, nodes: t.Any) -> None:
        pass

    def pull_dependencies(self, nodes: t.Any) -> None:
        pass

    def visit_Name(self, node: nodes.Name, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        if node.ctx == "store" and (
            frame.toplevel or frame.loop_frame or frame.block_frame
        ):
            if hasattr(self, "_assign_stack") and self._assign_stack:
                self._assign_stack[-1].add(node.name)

        if node.name in ("blocks", "debug_info"):
            self.write(node.name)
            return

        if node.ctx == "load":
            self.write(f"context.get({node.name!r})")
            return

        try:
            ref = frame.symbols.ref(node.name)

            if node.ctx == "load":
                from jinja2.compiler import VAR_LOAD_PARAMETER

                load = frame.symbols.find_load(ref)
                if not (
                    load is not None
                    and load[0] == VAR_LOAD_PARAMETER
                    and hasattr(self, "parameter_is_undeclared")
                    and not self.parameter_is_undeclared(ref)
                ):
                    self.write(
                        f"(undefined(name={node.name!r}) if {ref} is missing else {ref})"
                    )
                    return

            self.write(ref)
        except AssertionError:
            if node.ctx == "load":
                self.write(f"context.get({node.name!r}, undefined(name={node.name!r}))")
            else:
                self.write(f"context.vars[{node.name!r}]")

    def generate(self, node: nodes.Template) -> str:
        self.writeline(f"name = {self.name!r}")
        self.writeline("blocks = {}")
        self.writeline("debug_info = None")

        self.writeline("from jinja2.runtime import Undefined")
        self.writeline("def undefined(name=None, **_):")
        self.indent()
        self.writeline("return Undefined(name=name)")
        self.outdent()

        self.writeline("async def root(context):")
        self.indent()
        self.writeline("parent_template = None")
        self.writeline("environment = context.environment")
        self.writeline("eval_ctx = context.eval_ctx")
        self.writeline("missing = environment.undefined")

        from jinja2.nodes import EvalContext

        if self.eval_ctx is None:
            self.eval_ctx = EvalContext(self.environment, self.name)

        frame = self.root_frame_class(eval_ctx=self.eval_ctx)
        frame.toplevel = frame.rootlevel = True
        frame.require_output_check = False

        self.pull_locals(node.find_all(nodes.Scope))
        self.pull_dependencies(node.find_all((nodes.Import, nodes.FromImport)))
        self.blockvisit(node.body, frame)
        self.outdent()

        return self.stream.getvalue()

    def visit_For(self, node: nodes.For, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        node.iter_child_nodes(exclude=("iter",))
        if node.recursive:
            raise NotImplementedError("Recursive loops not supported")

        target = t.cast(t.Any, node.target)
        item = target.name

        frame.symbols.store(item)

        self.writeline(f"{item} = None")

        loop_filter = None
        if node.test:
            loop_filter = self.temporary_identifier()
            self.writeline(f"{loop_filter} = ", node.test)
            self.visit(node.test, frame)

        loop_var = self.temporary_identifier()
        self.writeline(f"{loop_var} = -1", node)

        self.writeline("try:", node)
        self.indent()
        self.writeline(f"async for {item} in ", node.iter)
        self.visit(node.iter, frame)
        self.write(":")
        self.indent()
        self.writeline(f"{loop_var} += 1")
        if node.test and loop_filter:
            self.writeline(f"if {loop_filter}({item}):")
            self.indent()
        self.blockvisit(node.body, frame)
        if node.test and loop_filter:
            self.outdent()
        self.outdent()
        self.outdent()
        self.writeline("except TypeError:", node)
        self.indent()

        self.writeline(f"for {item} in ", node.iter)
        self.visit(node.iter, frame)
        self.write(":")
        self.indent()
        self.writeline(f"{loop_var} += 1")
        if node.test and loop_filter:
            self.writeline(f"if {loop_filter}({item}):")
            self.indent()
        self.blockvisit(node.body, frame)
        if node.test and loop_filter:
            self.outdent()
        self.outdent()
        self.outdent()

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
