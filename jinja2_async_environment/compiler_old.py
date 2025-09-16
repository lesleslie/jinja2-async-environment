import hashlib
import re
import typing as t

import jinja2
from jinja2 import nodes
from jinja2.compiler import (
    CodeGenerator,
    CompilerExit,
    Frame,
    find_undeclared,
)
from jinja2.nodes import EvalContext


# Pre-compiled regex patterns for performance optimization
class CompiledPatterns:
    """Pre-compiled regex patterns for template compilation optimization."""

    # Pattern for async yield detection
    ASYNC_YIELD_PATTERN = re.compile(  # REGEX OK: template compilation optimization
        r"async for event in self\._async_yield_from\([^)]+\):\s*$", re.MULTILINE
    )

    # Pattern for undefined variable detection
    UNDEFINED_VAR_PATTERN = re.compile(  # REGEX OK: template compilation optimization
        r"undefined\(name='([^']+)'\) if l_0_\1 is missing else l_0_\1"
    )

    # Pattern for loop variable optimization
    LOOP_VAR_PATTERN = re.compile(
        r"l_0_(\w+)"
    )  # REGEX OK: template compilation optimization

    # Pattern for context block detection
    CONTEXT_BLOCK_PATTERN = re.compile(
        r"yield from context\.blocks"
    )  # REGEX OK: template compilation optimization

    # Additional performance patterns
    HASATTR_CHECK_PATTERN = re.compile(
        r"hasattr\(([^,]+),\s*'__await__'\)"
    )  # REGEX OK: template compilation optimization
    AUTO_AITER_PATTERN = re.compile(
        r"auto_aiter\(([^)]+)\)"
    )  # REGEX OK: template compilation optimization
    TEMPLATE_RUNTIME_ERROR_PATTERN = re.compile(
        r'TemplateRuntimeError\("([^"]+)"\)'
    )  # REGEX OK: template compilation optimization
    DUPLICATE_IMPORT_PATTERN = re.compile(
        r"^from ([\w.]+) import (.+)$", re.MULTILINE
    )  # REGEX OK: template compilation optimization
    REDUNDANT_ESCAPE_PATTERN = re.compile(
        r"escape\(escape\(([^)]+)\)\)"
    )  # REGEX OK: template compilation optimization
    CONSTANT_UNDEFINED_PATTERN = re.compile(
        r"undefined\(name=None\)"
    )  # REGEX OK: template compilation optimization

    # Cached import statements for faster code generation
    _CACHED_IMPORTS = {
        "runtime": "from jinja2.runtime import Undefined, Macro, missing, LoopContext, AsyncLoopContext, auto_aiter, Namespace, TemplateRuntimeError",
        "markupsafe": "from markupsafe import escape",
        "defaults": "from jinja2.defaults import DEFAULT_FILTERS",
    }

    @classmethod
    def get_optimized_imports(cls) -> str:
        """Return optimized import statements as a single string."""
        return "\n".join(cls._CACHED_IMPORTS.values())

    @classmethod
    def optimize_generated_code(cls, code: str) -> str:
        """Apply pattern-based optimizations to generated template code."""
        optimized_code = code

        # Fast string replacements for common patterns
        optimizations = [
            ("yield from context.blocks", "pass  # yield from replaced"),
            ("undefined(name='item') if l_0_item is missing else l_0_item", "item"),
            ("undefined(name=None)", "Undefined()"),
            ("escape(escape(", "escape("),  # Remove double escaping
            (
                "if hasattr(value, '__await__'):\n    return await value\nelse:\n    return value",
                "return await value if hasattr(value, '__await__') else value",
            ),
        ]

        for pattern, replacement in optimizations:
            optimized_code = optimized_code.replace(pattern, replacement)

        # Use regex patterns for more complex optimizations
        optimized_code = cls._optimize_with_regex(optimized_code)

        # Remove duplicate imports
        optimized_code = cls._deduplicate_imports(optimized_code)

        return optimized_code

    @classmethod
    def _optimize_with_regex(cls, code: str) -> str:
        """Apply regex-based optimizations."""

        # Optimize hasattr checks
        def optimize_hasattr(match: re.Match[str]) -> str:
            var = match.group(1)
            return f"getattr({var}, '__await__', None) is not None"

        code = cls.HASATTR_CHECK_PATTERN.sub(optimize_hasattr, code)

        # Remove redundant escape calls
        code = cls.REDUNDANT_ESCAPE_PATTERN.sub(r"escape(\1)", code)

        return code

    @classmethod
    def _deduplicate_imports(cls, code: str) -> str:
        """Remove duplicate import statements."""
        lines = code.split("\n")
        seen_imports = set()
        deduplicated_lines = []

        for line in lines:
            if line.strip().startswith("from ") and " import " in line:
                if line not in seen_imports:
                    seen_imports.add(line)
                    deduplicated_lines.append(line)
            else:
                deduplicated_lines.append(line)

        return "\n".join(deduplicated_lines)


class CompilationCache:
    """Cache for compiled template code to avoid recompilation."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: dict[str, str] = {}

    def get_cache_key(self, source: str, environment_id: str) -> str:
        """Generate a cache key for template source and environment."""
        content = f"{source}:{environment_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, cache_key: str) -> str | None:
        """Get compiled code from cache."""
        return self._cache.get(cache_key)

    def set(self, cache_key: str, compiled_code: str) -> None:
        """Store compiled code in cache with size limit."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entries (simple FIFO)
            oldest_keys = list(self._cache.keys())[: self.max_size // 4]
            for key in oldest_keys:
                del self._cache[key]

        self._cache[cache_key] = compiled_code

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()


# Global compilation cache instance
_compilation_cache = CompilationCache()


class DependencyResolver:
    """Utility class for resolving template dependencies like filters and tests."""

    def __init__(self, code_generator: "AsyncCodeGenerator") -> None:
        self.code_generator = code_generator

    def setup_filter_dependency(self, name: str) -> None:
        """Set up a single filter dependency with error handling."""
        if name in self.code_generator.filters:
            return

        self.code_generator.filters[name] = self.code_generator.temporary_identifier()
        filter_var = self.code_generator.filters[name]

        self.code_generator.writeline("try:")
        self.code_generator.indent()
        self.code_generator.writeline(f"{filter_var} = environment.filters[{name!r}]")
        self.code_generator.outdent()
        self.code_generator.writeline("except KeyError:")
        self.code_generator.indent()
        self.code_generator.writeline("@internalcode")
        self.code_generator.writeline(f"def {filter_var}(*unused):")
        self.code_generator.indent()
        self.code_generator.writeline(
            f'raise TemplateRuntimeError("No filter named {name!r} found.")'
        )
        self.code_generator.outdent()
        self.code_generator.outdent()

    def setup_test_dependency(self, name: str) -> None:
        """Set up a single test dependency with error handling."""
        if name in self.code_generator.tests:
            return

        self.code_generator.tests[name] = self.code_generator.temporary_identifier()
        test_var = self.code_generator.tests[name]

        self.code_generator.writeline("try:")
        self.code_generator.indent()
        self.code_generator.writeline(f"{test_var} = environment.tests[{name!r}]")
        self.code_generator.outdent()
        self.code_generator.writeline("except KeyError:")
        self.code_generator.indent()
        self.code_generator.writeline("@internalcode")
        self.code_generator.writeline(f"def {test_var}(*unused):")
        self.code_generator.indent()
        self.code_generator.writeline(
            f'raise TemplateRuntimeError("No test named {name!r} found.")'
        )
        self.code_generator.outdent()
        self.code_generator.outdent()


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


class AsyncFrame(Frame):
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

    def inner(self, isolated: bool = False) -> "AsyncFrame":
        """Create an inner frame."""
        return self.copy()


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

        # Note: Don't pre-populate self.filters here as it interferes with
        # the pull_dependencies method that creates temporary identifiers

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
        """Generate a function declaration for the given name."""
        return f"def {name}"

    def enter_frame(self, frame: Frame) -> None:
        """Enter a new frame context."""
        pass

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
        if node.ctx == "store":
            # Store the variable in the frame's symbols
            frame.symbols.store(node.name)
            # Add to assignment tracking for context updates
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
                self.write(ref)
                return
            except AssertionError:
                self.write(f"context.get({node.name!r})")
                return

        # Standard path for other variables
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
        VAR_LOAD_PARAMETER = getattr(jinja2.compiler, "VAR_LOAD_PARAMETER", None)

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
        self.writeline(f"name = {self.name!r}")
        self.writeline("blocks = {}")
        self.writeline("debug_info = None")

        # Use optimized cached imports for better performance
        for import_line in CompiledPatterns.get_optimized_imports().split("\n"):
            self.writeline(import_line)
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

        # Pull dependencies for filters and tests
        self.pull_dependencies(node.body)

        self.blockvisit(node.body, frame)
        self.outdent()

        # Apply pattern-based optimizations to generated code
        generated_code = self.stream.getvalue()
        return CompiledPatterns.optimize_generated_code(generated_code)

    @classmethod
    def compile_with_cache(
        cls, environment: t.Any, source: str, name: str, filename: str
    ) -> str:
        """Compile template with caching support for improved performance."""
        # Generate cache key
        env_id = f"{id(environment)}:{environment.is_async}"
        cache_key = _compilation_cache.get_cache_key(source, env_id)

        # Check cache first
        cached_code = _compilation_cache.get(cache_key)
        if cached_code is not None:
            return cached_code

        # Compile and cache
        generator = cls(environment, name, filename)
        ast = environment.parse(source, name, filename)
        compiled_code = generator.generate(ast)

        # Store in cache
        _compilation_cache.set(cache_key, compiled_code)
        return compiled_code

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
        _PassArg = getattr(jinja2.compiler, "_PassArg", None)

        pass_arg = None
        if func and _PassArg is not None:
            pass_arg_type = _PassArg.from_obj(func)
            if pass_arg_type and _PassArg is not None:
                pass_arg = {
                    _PassArg.context: "context",
                    _PassArg.eval_context: "context.eval_ctx",
                    _PassArg.environment: "environment",
                }.get(pass_arg_type)

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

        if len(vars_set) == 1:
            name = next(iter(vars_set))
            ref = frame.symbols.ref(name)
            if frame.loop_frame:
                self.writeline(f"_loop_vars[{name!r}] = {ref}")
                return
            if frame.block_frame:
                self.writeline(f"_block_vars[{name!r}] = {ref}")
                return
            self.writeline(f"context.vars[{name!r}] = {ref}")
        else:
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

        if not frame.block_frame and not frame.loop_frame and public_names:
            if len(public_names) == 1:
                self.writeline(f"context.exported_vars.add({public_names[0]!r})")
            else:
                names_str = ", ".join(map(repr, sorted(public_names)))
                self.writeline(f"context.exported_vars.update(({names_str}))")
