import typing as t

from jinja2 import nodes
from jinja2.compiler import CodeGenerator
from jinja2.compiler import CompilerExit
from jinja2.compiler import Frame


class AsyncCodeGenerator(CodeGenerator):
    def visit_Block(self, node: nodes.Block, frame: Frame) -> None:
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
        if not self.environment.is_async and frame.buffer is None:
            self.writeline(
                f"yield from context.blocks[{node.name!r}][0]({context})", node
            )
        else:
            self.writeline(
                f"{self.choose_async()}for event in"
                f" context.blocks[{node.name!r}][0]({context}):",
                node,
            )
            self.indent()
            self.simple_write("event", frame)
            self.outdent()
        self.outdent(level)

    def visit_Extends(self, node: nodes.Extends, frame: Frame) -> None:
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
        self.writeline(
            f"parent_template = "
            f"{self.choose_async('await ')}environment.get_template(",
            node,
        )
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
        if node.ignore_missing:
            self.writeline("try:")
            self.indent()
        func_name = "get_or_select_template"
        if isinstance(node.template, nodes.Const):
            if isinstance(node.template.value, str):
                func_name = "get_template"
            elif isinstance(node.template.value, (tuple, list)):
                func_name = "select_template"
        elif isinstance(node.template, (nodes.Tuple, nodes.List)):
            func_name = "select_template"
        self.writeline(
            f"template = {self.choose_async('await ')}environment.{func_name}(", node
        )
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
        skip_event_yield = False
        if node.with_context:
            self.writeline(
                f"{self.choose_async()}for event in template.root_render_func("
                "template.new_context(context.get_all(), True,"
                f" {self.dump_local_context(frame)})):"
            )
        elif self.environment.is_async:
            self.writeline(
                "for event in (await template._get_default_module_async())"
                "._body_stream:"
            )
        else:
            self.writeline("yield from template._get_default_module()._body_stream")
            skip_event_yield = True
        if not skip_event_yield:
            self.indent()
            self.simple_write("event", frame)
            self.outdent()
        if node.ignore_missing:
            self.outdent()

    def _import_common(
        self, node: t.Union[nodes.Import, nodes.FromImport], frame: Frame
    ) -> None:
        self.write(f"{self.choose_async('await ')}environment.get_template(")
        self.visit(node.template, frame)
        self.write(f", {self.name!r}).")
        if node.with_context:
            f_name = f"make_module{self.choose_async('_async')}"
            self.write(
                f"{f_name}(context.get_all(), True, {self.dump_local_context(frame)})"
            )
        else:
            self.write(f"_get_default_module{self.choose_async('_async')}(context)")
