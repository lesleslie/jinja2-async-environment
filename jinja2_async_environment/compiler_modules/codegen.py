"""Async code generator for template compilation."""

import typing as t

from jinja2 import nodes
from jinja2.compiler import (
    CodeGenerator,
    Frame,
    find_undeclared,
)

from .cache import CompilationCache
from .dependencies import DependencyResolver
from .frame import AsyncFrame
from .loops import LoopCodeGenerator
from .patterns import CompiledPatterns

if t.TYPE_CHECKING:
    pass

# Global compilation cache instance
_compilation_cache = CompilationCache()


class AsyncCodeGenerator(CodeGenerator):
    """Async-aware code generator extending Jinja2's CodeGenerator."""

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

    # Fast lookup cache for common variable names
    _COMMON_VARS = frozenset(
        [
            "context",
            "environment",
            "eval_ctx",
            "undefined",
            "item",
            "loop",
            "block",
            "value",
            "name",
            "key",
        ]
    )

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

        # Initialize assignment tracking stack
        self._assign_stack: list[set[str]] = []

        # Initialize utility classes for better code organization
        self._dependency_resolver = DependencyResolver(self)
        self._loop_generator = LoopCodeGenerator(self)

        from jinja2.nodes import EvalContext

        if self.eval_ctx is None:
            self.eval_ctx = EvalContext(self.environment, self.name)

    def choose_async(self, async_fmt: str = "async ", sync_fmt: str = "") -> str:  # type: ignore[override]
        return async_fmt if self.environment.enable_async else sync_fmt

    def simple_write(self, value: str, frame: Frame) -> None:  # type: ignore[override]
        self.writeline(f"yield {value}")

    def func_code_generator(self, frame: Frame) -> str:
        async_frame = t.cast(AsyncFrame, frame)
        return "async def" if async_frame.is_async else "def"

    def func(self, name: str) -> str:
        """Generate a function declaration for the given name.

        Properly handles async functions by checking environment.is_async.
        """
        return f"{self.choose_async()}def {name}"

    def enter_frame(self, frame: Frame) -> None:
        """Enter a new frame context and load variables from context.

        This method generates code to resolve template variables from the
        context and assign them to local frame variables (e.g., l_0_name).
        """
        from jinja2.compiler import (
            VAR_LOAD_ALIAS,  # type: ignore[attr-defined]
            VAR_LOAD_PARAMETER,  # type: ignore[attr-defined]
            VAR_LOAD_RESOLVE,  # type: ignore[attr-defined]
            VAR_LOAD_UNDEFINED,  # type: ignore[attr-defined]
        )

        undefs = []
        for target, (action, param) in frame.symbols.loads.items():
            if action == VAR_LOAD_PARAMETER:
                pass
            elif action == VAR_LOAD_RESOLVE:
                self.writeline(f"{target} = {self.get_resolve_func()}({param!r})")
            elif action == VAR_LOAD_ALIAS:
                self.writeline(f"{target} = {param}")
            elif action == VAR_LOAD_UNDEFINED:
                undefs.append(target)
            else:
                raise NotImplementedError("unknown load instruction")
        if undefs:
            self.writeline(f"{' = '.join(undefs)} = missing")

    def leave_frame(self, frame: Frame, with_python_scope: bool = False) -> None:
        """Leave a frame context."""
        pass

    def return_buffer_contents(
        self,
        frame: Frame,
        force_unescaped: bool = False,  # noqa: ARG002
    ) -> None:
        _ = force_unescaped
        if frame.buffer is not None:
            self.writeline(f"return ''.join({frame.buffer})")

    def visit_Name(self, node: nodes.Name, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        self._handle_assignment_tracking(node, frame)
        if self._handle_special_names(node):
            return
        self._handle_symbol_name(node, frame)

    def _handle_assignment_tracking(self, node: nodes.Name, frame: AsyncFrame) -> None:
        if node.ctx == "store":
            frame.symbols.store(node.name)
            if frame.toplevel or frame.loop_frame or frame.block_frame:
                if hasattr(self, "_assign_stack") and self._assign_stack:
                    self._assign_stack[-1].add(node.name)

    def _handle_special_names(self, node: nodes.Name) -> bool:
        if node.name in ("blocks", "debug_info"):
            self.write(node.name)
            return True
        return False

    def _handle_symbol_name(self, node: nodes.Name, frame: AsyncFrame) -> None:
        # Fast path for common variables
        if node.name in self._COMMON_VARS and node.ctx == "load":
            try:
                ref = frame.symbols.ref(node.name)
                # Add undefined check for ALL variables, including common ones
                # This ensures proper undefined variable handling
                self.write(
                    f"(undefined(name={node.name!r}) if {ref} is missing else {ref})"
                )
                return
            except AssertionError:
                self.write(f"context.get({node.name!r})")
                return

        # Standard path for other variables
        try:
            ref = frame.symbols.ref(node.name)
            if node.ctx == "load":
                # ALWAYS use undefined check for variables loaded from context
                # This ensures missing variables render as Undefined() instead of "missing"
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
        # Try to get VAR_LOAD_PARAMETER using getattr to avoid import issues
        try:
            import jinja2.compiler

            VAR_LOAD_PARAMETER = getattr(jinja2.compiler, "VAR_LOAD_PARAMETER", None)
        except (ImportError, AttributeError):
            # If we can't access it, we can't use it
            return False

        if VAR_LOAD_PARAMETER is None:
            return False

        load = frame.symbols.find_load(ref)
        return not (
            load is not None
            and load[0] == VAR_LOAD_PARAMETER
            and hasattr(self, "parameter_is_undeclared")
            and not self.parameter_is_undeclared(ref)
        )

    def pull_dependencies(self, nodes: t.Iterable[nodes.Node]) -> None:
        """Find all filter and test names used in the template and assign them to variables."""
        from jinja2.compiler import DependencyFinderVisitor

        visitor = DependencyFinderVisitor()
        for node in nodes:
            visitor.visit(node)

        # Set up filter dependencies using utility class
        for name in sorted(visitor.filters):
            self._dependency_resolver.setup_filter_dependency(name)

        # Set up test dependencies using utility class
        for name in sorted(visitor.tests):
            self._dependency_resolver.setup_test_dependency(name)

    def generate(self, node: nodes.Template) -> str:
        """Generate template code following base Jinja2 architecture.

        Architecture (matching base Jinja2):
        1. Pre-discover all blocks and store in self.blocks
        2. Generate imports and module-level setup
        3. Generate root function with block CALLS
        4. After root exits, generate all block DEFINITIONS
        5. Generate module-level blocks dict

        This separation of block calling vs. definition is CRITICAL for
        template inheritance to work correctly.
        """
        from jinja2.nodes import EvalContext

        if self.eval_ctx is None:
            self.eval_ctx = EvalContext(self.environment, self.name)

        # PHASE 1: Pre-discover all blocks (like base Jinja2)
        # This must happen BEFORE any code generation so blocks are known
        for block in node.find_all(nodes.Block):
            if block.name in self.blocks:
                self.fail(f"block {block.name!r} defined twice", block.lineno)
            self.blocks[block.name] = block

        # Check if template has extends (for proper frame configuration)
        have_extends = node.find(nodes.Extends) is not None

        # PHASE 2: Module-level setup
        # Use optimized cached imports for better performance
        for import_line in CompiledPatterns.get_optimized_imports().split("\n"):
            self.writeline(import_line)

        self.writeline(f"name = {self.name!r}")

        # Helper functions
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

        # PHASE 3: Generate root render function
        self.writeline("async def root(context):")
        self.indent()

        # CRITICAL: Write commons sets up resolve, undefined, concat, etc.
        # AND includes "if 0: yield None" to make function an async generator
        self.writeline("resolve = context.resolve_or_missing")
        self.writeline("undefined = environment.undefined")
        self.writeline("concat = environment.concat")
        self.writeline("cond_expr_undefined = Undefined")
        self.writeline("if 0: yield None")  # Makes function an async generator

        # Create frame for root processing
        frame = self.root_frame_class(eval_ctx=self.eval_ctx)

        # Check for 'self' usage BEFORE analyzing
        if "self" in find_undeclared(node.body, ("self",)):
            ref = frame.symbols.declare_parameter("self")
            self.writeline(f"{ref} = TemplateReference(context)")

        # Analyze node to discover variables
        frame.symbols.analyze_node(node)

        # Set frame flags AFTER analysis
        frame.toplevel = frame.rootlevel = True
        frame.require_output_check = have_extends and not self.has_known_extends

        # Initialize parent_template for extends
        if have_extends:
            self.writeline("parent_template = None")

        # Enter frame and process template body
        # visit_Block will be called during blockvisit, but now it only CALLS blocks
        self.enter_frame(frame)
        self.pull_dependencies(node.body)
        self.blockvisit(node.body, frame)
        self.leave_frame(frame, with_python_scope=True)
        self.outdent()  # Exit root function

        # PHASE 4: Parent template iteration (if extends present)
        if have_extends:
            if not self.has_known_extends:
                self.indent()
                self.writeline("if parent_template is not None:")
            self.indent()
            # Generate async parent template iteration
            self.writeline("agen = parent_template.root_render_func(context)")
            self.writeline("try:")
            self.indent()
            self.writeline("async for event in agen:")
            self.indent()
            self.writeline("yield event")
            self.outdent()
            self.outdent()
            self.writeline("finally: await agen.aclose()")
            self.outdent(1 + (not self.has_known_extends))

        # PHASE 5: Generate all block function DEFINITIONS
        # This happens AFTER root function exits
        self._generate_block_functions()

        # PHASE 6: Generate module-level blocks dict
        blocks_kv_str = ", ".join(f"{name!r}: block_{name}" for name in self.blocks)
        self.writeline(f"blocks = {{{blocks_kv_str}}}", extra=1)
        self.writeline("debug_info = None")

        # Apply pattern-based optimizations to generated code
        generated_code = self.stream.getvalue()
        return CompiledPatterns.optimize_generated_code(generated_code)

    def _generate_block_functions(self) -> None:
        """Generate all block function definitions.

        This is called AFTER the root function exits, following base Jinja2's
        architecture. Block functions are defined separately from where they're
        called to enable proper template inheritance.

        For each block in self.blocks:
        - Creates async def block_NAME(context) function
        - Adds write_commons() for generator setup
        - Processes block body with proper frame
        - Handles 'self' and 'super' references
        """
        for name, block_node in self.blocks.items():
            # Start block function definition
            self.writeline(
                f"async def block_{name}(context):",
                block_node,
                1,
            )
            self.indent()

            # Write commons (includes "if 0: yield None" for generator)
            self.writeline("resolve = context.resolve_or_missing")
            self.writeline("undefined = environment.undefined")
            self.writeline("concat = environment.concat")
            self.writeline("cond_expr_undefined = Undefined")
            self.writeline("if 0: yield None")  # Makes function an async generator

            # Create block frame (NOT a child of toplevel frame)
            block_frame = self.root_frame_class(eval_ctx=self.eval_ctx)
            block_frame.block_frame = True

            # Check for 'self' and 'super' usage
            undeclared = find_undeclared(block_node.body, ("self", "super"))
            if "self" in undeclared:
                ref = block_frame.symbols.declare_parameter("self")
                self.writeline(f"{ref} = TemplateReference(context)")
            if "super" in undeclared:
                ref = block_frame.symbols.declare_parameter("super")
                self.writeline(f"{ref} = context.super({name!r}, block_{name})")

            # Analyze block body
            block_frame.symbols.analyze_node(block_node)
            block_frame.block = name

            # Block-level variables dict
            self.writeline("_block_vars = {}")

            # Enter frame, process block body, leave frame
            self.enter_frame(block_frame)
            self.pull_dependencies(block_node.body)
            self.blockvisit(block_node.body, block_frame)
            self.leave_frame(block_frame, with_python_scope=True)

            self.outdent()  # Exit block function

    def visit_Block(self, node: nodes.Block, frame: Frame) -> None:
        """Call a block and register it for the template.

        This method ONLY handles CALLING blocks from context.blocks.
        Block DEFINITIONS are generated separately in _generate_block_functions().

        This separation is CRITICAL for template inheritance to work:
        - Child templates can override parent blocks via context.blocks
        - Blocks are discovered and defined after root function exits
        - During root execution, blocks are called from context.blocks[name][0]

        Architecture matches base Jinja2's CodeGenerator.visit_Block.
        """
        block_name = node.name

        # Handle inheritance conditional
        level = 0
        if frame.toplevel:
            # If we know we're a child template, no need to check
            if self.has_known_extends:
                return
            # If we've seen extends before, add conditional
            if self.extends_so_far > 0:
                self.writeline("if parent_template is None:")
                self.indent()
                level += 1

        # Determine context reference (scoped blocks use derived context)
        if node.scoped:
            context = self.derive_context(frame)
        else:
            context = self.get_context_ref()

        # Check if block is required
        if node.required:
            self.writeline(f"if len(context.blocks[{block_name!r}]) <= 1:", node)
            self.indent()
            self.writeline(
                f'raise TemplateRuntimeError("Required block {block_name!r} not found")',
                node,
            )
            self.outdent()

        # CRITICAL: Call block from context.blocks (enables inheritance)
        # context.blocks[name] is a list, [0] gets the first (child's override or base)
        self.writeline(f"gen = context.blocks[{block_name!r}][0]({context})")
        self.writeline("try:")
        self.indent()
        self.writeline("async for event in gen:")
        self.indent()
        self.simple_write("event", frame)
        self.outdent()
        self.outdent()
        self.writeline("finally: await gen.aclose()")

        # Close inheritance conditional if needed
        self.outdent(level)

    def visit_Extends(self, node: nodes.Extends, frame: Frame) -> None:
        """Visit an extends node with proper async handling."""
        # Frame is already cast to AsyncFrame through method signature compatibility

        # If output check is not required, raise CompilerExit immediately
        if not frame.require_output_check:
            from jinja2.compiler import CompilerExit

            raise CompilerExit()

        # Check if we're in a top-level scope
        if not frame.toplevel:
            self.fail("cannot use extend from a non top-level scope", node.lineno)

        # Handle multiple extends
        if self.extends_so_far > 0:
            if not self.has_known_extends:
                self.writeline("if parent_template is not None:")
                self.indent()
            self.writeline('raise TemplateRuntimeError("extended multiple times")')
            if self.has_known_extends:
                from jinja2.compiler import CompilerExit

                raise CompilerExit()
            else:
                self.outdent()

        # Generate async template loading code
        self.writeline("parent_template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")
        self.writeline("for name, parent_block in parent_template.blocks.items():")
        self.indent()
        self.writeline("context.blocks.setdefault(name, []).append(parent_block)")
        self.outdent()

        # Update inheritance tracking
        if frame.rootlevel:
            self.has_known_extends = True
        self.extends_so_far += 1

    def visit_Include(self, node: nodes.Include, frame: Frame) -> None:
        """Visit an include node with proper async handling."""
        # Frame is already cast to AsyncFrame through method signature compatibility

        # Handle ignore_missing flag
        if node.ignore_missing:
            self.writeline("try:")
            self.indent()

        # Generate async template loading code
        self.writeline("template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")

        # Close try block for ignore_missing
        if node.ignore_missing:
            self.outdent()
            self.writeline("except TemplateNotFound:")
            self.indent()
            self.writeline("pass")
            self.outdent()
            self.writeline("else:")
            self.indent()

        # Generate rendering code based on context flag
        if node.with_context:
            # With context - include local variables
            local_context = self.dump_local_context(frame)
            self.writeline(
                f"async for event in template.root_render_func(template.new_context(context.get_all(), True, {local_context})):"
            )
        else:
            # Without context - use default module
            self.writeline(
                "async for event in (await template._get_default_module_async())._body_stream:"
            )

        # Generate event output
        self.indent()
        self.simple_write("event", frame)
        self.outdent()

        # Close else block for ignore_missing
        if node.ignore_missing:
            self.outdent()

    def visit_AsyncFor(self, node: nodes.For, frame: Frame) -> None:
        """Visit an async for loop node with proper async handling."""
        # Frame is already cast to AsyncFrame through method signature compatibility

        # Handle recursive loops (not supported)
        if node.recursive:
            raise NotImplementedError("Recursive loops not supported")

        # Get target variable name
        target = node.target
        if isinstance(target, nodes.Name):
            item = target.name
        else:
            item = "item"
        frame.symbols.store(item)

        # Initialize target variable
        self.writeline(f"{item} = None")

        # Handle loop filter
        loop_filter = None
        if hasattr(node, "test") and node.test:
            loop_filter = self.temporary_identifier()
            self.writeline(f"{loop_filter} = ", node.test)
            self.visit(node.test, frame)

        # Initialize loop counter
        loop_var = self.temporary_identifier()
        self.writeline(f"{loop_var} = -1", node)

        # Generate async for loop
        self.writeline(f"async for {item} in ", node.iter)
        self.visit(node.iter, frame)
        self.write(":")
        self.indent()

        # Increment loop counter
        self.writeline(f"{loop_var} += 1")

        # Handle loop filter condition
        if hasattr(node, "test") and node.test and loop_filter:
            self.writeline(f"if {loop_filter}({item}):")
            self.indent()

        # Process loop body
        if hasattr(node, "body"):
            self.blockvisit(node.body, frame)

        # Close filter condition
        if hasattr(node, "test") and node.test and loop_filter:
            self.outdent()

        # Close main loop
        self.outdent()

        # Handle else clause
        if hasattr(node, "else_") and node.else_:
            self.writeline(f"if {loop_var} == -1:")
            self.indent()
            self.blockvisit(node.else_, frame)
            self.outdent()

    def visit_AsyncCall(self, node: nodes.Call, frame: Frame) -> None:
        """Visit an async call node by adding await prefix."""
        self.write("await ")
        self.visit_Call(node, frame)

    def visit_AsyncFilterBlock(self, node: nodes.FilterBlock, frame: Frame) -> None:
        """Visit an async filter block node."""
        # Frame is already cast to AsyncFrame through method signature compatibility

        # Early return if no filter or body
        if not hasattr(node, "filter"):
            return
        if not hasattr(node, "body"):
            return

        # Get filter node
        filter_node = node.filter

        # Create buffer for collecting content
        buffer = self.temporary_identifier()
        self.writeline(f"{buffer} = []")

        # Create async frame for processing body
        asyncframe = frame.copy()
        asyncframe.buffer = buffer
        asyncframe.toplevel = False

        # Process the body
        self.blockvisit(node.body, asyncframe)

        # Generate await call for filter
        self.writeline("await ", filter_node)
        self.visit(filter_node, frame)
        self.write(f"(''.join({buffer}))")

    def visit_AsyncBlock(self, node: nodes.Block, frame: Frame) -> None:
        """Visit an async block node."""
        # Frame is already cast to AsyncFrame through method signature compatibility

        # Early return if no name or body
        if not hasattr(node, "name"):
            return
        if not hasattr(node, "body"):
            return

        # Get block name
        block_name = node.name

        # Initialize block storage
        self.writeline(f"blocks[{block_name!r}] = []")

        # Define async block function
        block_func_name = f"block_{block_name}"
        self.writeline(f"async def {block_func_name}(context):")
        self.indent()

        # Empty block content placeholder
        self.writeline("yield ''")

        # Process block body if it exists
        if node.body:
            self.blockvisit(node.body, frame)

        # End function and register block
        self.outdent()
        self.writeline(f"blocks[{block_name!r}].append({block_func_name})")

    def _import_common(
        self, node: nodes.Import | nodes.FromImport, frame: Frame
    ) -> None:
        """Common import functionality with async template loading."""
        # Cast frame to AsyncFrame for type safety
        frame = t.cast(AsyncFrame, frame)

        # Generate async template loading code
        self.writeline("template = await environment.get_template_async(", node)
        self.visit(node.template, frame)
        self.write(f", {self.name!r})")

    @classmethod
    def compile_with_cache(
        cls, environment: t.Any, source: str, name: str, filename: str
    ) -> str:
        """Compile template with caching support for improved performance."""
        # Try to use environment's cache manager first, fall back to global cache
        cache_manager = getattr(environment, "cache_manager", None)
        if cache_manager:
            # Use environment's cache manager
            import hashlib

            env_id = f"{id(environment)}:{getattr(environment, 'is_async', False)}"
            content = f"{source}:{env_id}"
            cache_key = hashlib.sha256(content.encode()).hexdigest()[:16]

            # Check cache first
            cached_code_first: str | None = cache_manager.get("compilation", cache_key)
            if cached_code_first is not None:
                return cached_code_first

            # Compile and cache
            generator = cls(environment, name, filename)

            ast = environment.parse(source, name, filename)
            compiled_code_first: str = generator.generate(ast)

            # Store in cache
            cache_manager.set("compilation", cache_key, compiled_code_first)
            return compiled_code_first
        else:
            # Fall back to global cache for backward compatibility
            env_id = f"{id(environment)}:{getattr(environment, 'is_async', False)}"
            cache_key = _compilation_cache.get_cache_key(source, env_id)

            # Check cache first
            cached_code_second: str | None = _compilation_cache.get(cache_key)
            if cached_code_second is not None:
                return cached_code_second

            # Compile and cache
            generator = cls(environment, name, filename)

            ast = environment.parse(source, name, filename)
            compiled_code_second: str = generator.generate(ast)

            # Store in cache
            _compilation_cache.set(cache_key, compiled_code_second)
            return compiled_code_second

    def visit_For(self, node: nodes.For, frame: Frame) -> None:
        frame = t.cast(AsyncFrame, frame)
        if node.recursive:
            raise NotImplementedError("Recursive loops not supported")

        # Create frames and setup
        loop_frame, test_frame, else_frame = self._setup_for_frames(frame)
        extended_loop, loop_ref = self._setup_for_loop_context(node, loop_frame)

        # Analyze nodes for variable declarations
        self._analyze_for_nodes(node, loop_frame, else_frame)

        # Handle loop filter
        loop_filter_func = self._setup_for_filter(node, test_frame, loop_frame)

        # Setup loop variables and checks
        self._setup_for_variables(node, extended_loop, loop_ref)

        # Generate main loop
        iteration_indicator = self._generate_for_loop(
            node, frame, loop_frame, extended_loop, loop_ref, loop_filter_func
        )

        # Handle else clause
        self._handle_for_else(node, else_frame, iteration_indicator)

        # Cleanup
        self._cleanup_for_assignments(loop_frame)

    def _setup_for_frames(
        self, frame: AsyncFrame
    ) -> tuple[AsyncFrame, AsyncFrame, AsyncFrame]:
        """Setup frames for different scopes in for loop."""
        loop_frame = frame.inner()
        loop_frame.loop_frame = True
        test_frame = frame.inner()
        else_frame = frame.inner()
        return loop_frame, test_frame, else_frame

    def _setup_for_loop_context(
        self, node: nodes.For, loop_frame: AsyncFrame
    ) -> tuple[bool, str | None]:
        """Setup extended loop context and loop reference."""
        extended_loop = (
            node.recursive
            or "loop"
            in find_undeclared(node.iter_child_nodes(only=("body",)), ("loop",))
            or any(block.scoped for block in node.find_all(nodes.Block))
        )

        loop_ref = None
        if extended_loop:
            loop_ref = loop_frame.symbols.declare_parameter("loop")

        return extended_loop, loop_ref

    def _analyze_for_nodes(
        self, node: nodes.For, loop_frame: AsyncFrame, else_frame: AsyncFrame
    ) -> None:
        """Analyze nodes for variable declarations."""
        loop_frame.symbols.analyze_node(node, for_branch="body")
        if node.else_:
            else_frame.symbols.analyze_node(node, for_branch="else")

    def _setup_for_filter(
        self, node: nodes.For, test_frame: AsyncFrame, loop_frame: AsyncFrame
    ) -> str | None:
        """Setup loop filter if present."""
        if not node.test:
            return None

        loop_filter_func = self.temporary_identifier()
        test_frame.symbols.analyze_node(node, for_branch="test")
        self.writeline(f"{self.func(loop_filter_func)}(filter):", node.test)
        self.indent()
        self.enter_frame(test_frame)
        self.writeline(self.choose_async("async for ", "for "))
        self.visit(node.target, loop_frame)
        self.write(" in ")
        self.write(self.choose_async("auto_aiter(filter)", "filter"))
        self.write(":")
        self.indent()
        self.writeline("if ", node.test)
        self.visit(node.test, test_frame)
        self.write(":")
        self.indent()
        self.writeline("yield ")
        self.visit(node.target, loop_frame)
        self.outdent(3)
        self.leave_frame(test_frame, with_python_scope=True)
        return loop_filter_func

    def _setup_for_variables(
        self, node: nodes.For, extended_loop: bool, loop_ref: str | None
    ) -> None:
        """Setup loop variables and check for conflicts."""
        if extended_loop and loop_ref:
            self.writeline(f"{loop_ref} = missing")

        for name in node.find_all(nodes.Name):
            if name.ctx == "store" and name.name == "loop":
                self.fail(
                    "Can't assign to special loop variable in for-loop target",
                    name.lineno,
                )

    def _generate_for_loop(
        self,
        node: nodes.For,
        frame: AsyncFrame,
        loop_frame: AsyncFrame,
        extended_loop: bool,
        loop_ref: str | None,
        loop_filter_func: str | None,
    ) -> str | None:
        """Generate the main for loop code."""
        # Handle else clause iteration indicator
        iteration_indicator = None
        if node.else_:
            iteration_indicator = self.temporary_identifier()
            self.writeline(f"{iteration_indicator} = 1")

        # Generate the main loop using utility class
        self._loop_generator.generate_async_for_header(node, node.target, loop_frame)
        self._loop_generator.generate_loop_iterator(
            node.iter, frame, extended_loop, loop_ref, loop_filter_func
        )

        self.indent()
        self.enter_frame(loop_frame)

        self.writeline("_loop_vars = {}")
        self.blockvisit(node.body, loop_frame)
        if node.else_:
            self.writeline(f"{iteration_indicator} = 0")
        self.outdent()
        self.leave_frame(loop_frame, with_python_scope=not node.else_)

        return iteration_indicator

    def _handle_for_else(
        self, node: nodes.For, else_frame: AsyncFrame, iteration_indicator: str | None
    ) -> None:
        """Handle the else clause of for loop."""
        if not node.else_ or not iteration_indicator:
            return

        self.writeline(f"if {iteration_indicator}:")
        self.indent()
        self.enter_frame(else_frame)
        self.blockvisit(node.else_, else_frame)
        self.leave_frame(else_frame)
        self.outdent()

    def _cleanup_for_assignments(self, loop_frame: AsyncFrame) -> None:
        """Clear assignments made in the loop from the top level."""
        if hasattr(self, "_assign_stack") and self._assign_stack:
            self._assign_stack[-1].difference_update(loop_frame.symbols.stores)

    def visit_Macro(self, node: nodes.Macro, frame: Frame) -> None:
        """Visit a macro node and generate async-aware code."""
        frame = t.cast(AsyncFrame, frame)
        # For now, let's just use the base class implementation without modification
        # This ensures macros work in sync mode, and we can enhance async support later
        super().visit_Macro(node, frame)

    def visit_Filter(self, node: nodes.Filter, frame: Frame) -> None:
        """Visit a filter node and generate async-aware code."""
        frame = t.cast(AsyncFrame, frame)

        filter_ref = self._get_filter_reference(node)
        func = self.environment.filters.get(node.name)

        if self.environment.is_async:
            self.write("(await auto_await(")

        self.write(f"{filter_ref}(")
        self._write_filter_special_params(func)
        self._write_filter_input(node, frame)
        self._write_filter_arguments(node, frame)
        self.write(")")

        if self.environment.is_async:
            self.write("))")

    def _get_filter_reference(self, node: nodes.Filter) -> str:
        """Get the filter reference from dependencies or fallback to environment."""
        if node.name in self.filters:
            return self.filters[node.name]
        return f"environment.filters[{node.name!r}]"

    def _write_filter_special_params(self, func: t.Any) -> None:
        """Write special parameters that some filters need."""
        # Try to get _PassArg using getattr to avoid import issues
        _PassArg_module = None
        try:
            import jinja2.compiler

            _PassArg_module = getattr(jinja2.compiler, "_PassArg", None)
        except (ImportError, AttributeError):
            _PassArg_module = None

        pass_arg = None
        if func and _PassArg_module is not None:
            pass_arg_type = _PassArg_module.from_obj(func)
            if pass_arg_type is not None:
                # Use getattr to safely access attributes
                context_attr = getattr(_PassArg_module, "context", None)
                eval_context_attr = getattr(_PassArg_module, "eval_context", None)
                environment_attr = getattr(_PassArg_module, "environment", None)

                if context_attr is not None and pass_arg_type == context_attr:
                    pass_arg = "context"
                elif (
                    eval_context_attr is not None and pass_arg_type == eval_context_attr
                ):
                    pass_arg = "context.eval_ctx"
                elif environment_attr is not None and pass_arg_type == environment_attr:
                    pass_arg = "environment"

        if pass_arg is not None:
            self.write(f"{pass_arg}, ")

    def _write_filter_input(self, node: nodes.Filter, frame: AsyncFrame) -> None:
        """Write the filter input value."""
        if node.node is not None:
            self.visit(node.node, frame)
        elif frame.buffer is not None:
            self._write_buffer_content(frame)

    def _write_buffer_content(self, frame: AsyncFrame) -> None:
        """Write buffer content for filter blocks."""
        if frame.eval_ctx.volatile:
            self.write(
                f"(Markup(concat({frame.buffer}))"
                f" if context.eval_ctx.autoescape else concat({frame.buffer}))"
            )
        elif frame.eval_ctx.autoescape:
            self.write(f"Markup(concat({frame.buffer}))")
        else:
            self.write(f"concat({frame.buffer})")

    def _write_filter_arguments(self, node: nodes.Filter, frame: AsyncFrame) -> None:
        """Write filter arguments and keyword arguments."""
        for arg in node.args:
            self.write(", ")
            self.visit(arg, frame)

        for kwarg in node.kwargs:
            self.write(", ")
            self.visit(kwarg, frame)

        if node.dyn_args:
            self.write(", *")
            self.visit(node.dyn_args, frame)

        if node.dyn_kwargs:
            self.write(", **")
            self.visit(node.dyn_kwargs, frame)

    def visit_Assign(self, node: nodes.Assign, frame: Frame) -> None:
        """Visit an assignment node ({% set %} statements)."""
        frame = t.cast(AsyncFrame, frame)
        self.push_assign_tracking()

        # Check for namespace assignments like `ns.var = value`
        seen_refs: set[str] = set()
        for nsref in node.find_all(nodes.NSRef):
            if nsref.name in seen_refs:
                continue
            seen_refs.add(nsref.name)
            ref = frame.symbols.ref(nsref.name)
            self.writeline(f"if not isinstance({ref}, Namespace):")
            self.indent()
            self.writeline(
                "raise TemplateRuntimeError"
                '("cannot assign attribute on non-namespace object")'
            )
            self.outdent()

        # Generate the assignment code
        self.newline(node)
        self.visit(node.target, frame)
        self.write(" = ")
        self.visit(node.node, frame)
        self.pop_assign_tracking(frame)

    def push_assign_tracking(self) -> None:
        """Push a new layer for assignment tracking."""
        self._assign_stack.append(set())

    def pop_assign_tracking(self, frame: Frame) -> None:
        """Pop the topmost level for assignment tracking and update context variables."""
        frame = t.cast(AsyncFrame, frame)
        vars_set = self._assign_stack.pop()

        if (
            not frame.block_frame
            and not frame.loop_frame
            and not frame.toplevel
            or not vars_set
        ):
            return

        public_names = [x for x in vars_set if x[:1] != "_"]

        # Handle single variable case
        if len(vars_set) == 1:
            self._handle_single_variable(frame, vars_set)
        else:
            # Handle multiple variables case
            self._handle_multiple_variables(frame, vars_set)

        # Handle exported variables
        self._handle_exported_variables(frame, public_names)

    def _handle_single_variable(self, frame: AsyncFrame, vars_set: set[str]) -> None:
        """Handle the case with a single variable.

        Args:
            frame: Current frame
            vars_set: Set of variables
        """
        name = next(iter(vars_set))
        ref = frame.symbols.ref(name)
        if frame.loop_frame:
            self.writeline(f"_loop_vars[{name!r}] = {ref}")
        elif frame.block_frame:
            self.writeline(f"_block_vars[{name!r}] = {ref}")
        else:
            self.writeline(f"context.vars[{name!r}] = {ref}")

    def _handle_multiple_variables(self, frame: AsyncFrame, vars_set: set[str]) -> None:
        """Handle the case with multiple variables.

        Args:
            frame: Current frame
            vars_set: Set of variables
        """
        if frame.loop_frame:
            self.writeline("_loop_vars.update({")
        elif frame.block_frame:
            self.writeline("_block_vars.update({")
        else:
            self.writeline("context.vars.update({")

        for idx, name in enumerate(sorted(vars_set)):
            if idx:
                self.write(", ")
            ref = frame.symbols.ref(name)
            self.write(f"{name!r}: {ref}")
        self.write("})")

    def _handle_exported_variables(
        self, frame: AsyncFrame, public_names: list[str]
    ) -> None:
        """Handle exported variables.

        Args:
            frame: Current frame
            public_names: List of public variable names
        """
        if not frame.block_frame and not frame.loop_frame and public_names:
            if len(public_names) == 1:
                self.writeline(f"context.exported_vars.add({public_names[0]!r})")
            else:
                names_str = ", ".join(map(repr, sorted(public_names)))
                self.writeline(f"context.exported_vars.update(({names_str}))")
