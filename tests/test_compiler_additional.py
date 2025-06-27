from unittest.mock import MagicMock, patch

import pytest
from jinja2 import nodes
from jinja2_async_environment.compiler import AsyncCodeGenerator, AsyncFrame


@pytest.fixture
def async_code_generator() -> AsyncCodeGenerator:
    """Create an AsyncCodeGenerator instance for testing."""
    env = MagicMock()
    env.is_async = True
    return AsyncCodeGenerator(env, "test_template", "test.py")


@pytest.fixture
def async_frame() -> AsyncFrame:
    """Create an AsyncFrame instance for testing."""
    return AsyncFrame()


def test_async_frame_init() -> None:
    """Test initialization of AsyncFrame."""
    frame = AsyncFrame()
    assert frame.buffer is None  # Buffer is compatible with base Frame
    assert not frame.block_buffer
    assert frame.extended_buffer is None
    assert not frame.require_output_check
    assert not frame.toplevel
    assert not frame.rootlevel
    assert not frame.require_yield
    assert frame.buffer_count == 0
    assert not frame.is_async


def test_async_frame_copy() -> None:
    """Test the copy method of AsyncFrame."""
    frame = AsyncFrame()
    frame.buffer = "buffer_content"  # Use string for compatibility
    frame.block_buffer = ["block_buffer_item"]
    frame.extended_buffer = ["extended_buffer_item"]
    frame.require_output_check = True
    frame.toplevel = True
    frame.rootlevel = True
    frame.require_yield = True
    frame.buffer_count = 5
    frame.is_async = True

    copied_frame = frame.copy()

    assert copied_frame.buffer == frame.buffer
    assert copied_frame.block_buffer == frame.block_buffer
    assert copied_frame.extended_buffer == frame.extended_buffer
    assert copied_frame.require_output_check == frame.require_output_check
    assert copied_frame.toplevel == frame.toplevel
    assert copied_frame.rootlevel == frame.rootlevel
    assert copied_frame.require_yield == frame.require_yield
    assert copied_frame.buffer_count == frame.buffer_count
    assert copied_frame.is_async == frame.is_async


def test_async_code_generator_init() -> None:
    """Test initialization of AsyncCodeGenerator."""
    env = MagicMock()
    env.is_async = True
    generator = AsyncCodeGenerator(env, "test_template", "test.py")

    assert generator.environment is env
    assert generator.name == "test_template"
    assert generator.filename == "test.py"
    assert generator.stream is not None
    assert generator.extends_so_far == 0
    assert not generator.has_known_extends
    assert not generator.has_super
    assert callable(generator.buffer)  # buffer is now the inherited method
    assert generator.last_identifier == 0
    assert not generator.identifiers
    assert not generator.import_aliases
    assert not generator.blocks
    assert generator.extends_buffer is None
    assert not generator.required_blocks
    assert not generator.has_known_extends
    assert not generator.has_super


def test_visit_block(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_Block method."""
    # Create a mock Block node with all required attributes
    block_node = MagicMock(spec=nodes.Block)
    block_node.name = "test_block"
    block_node.body = MagicMock(spec=nodes.Template)
    block_node.scoped = False
    block_node.required = False

    # Create a mock frame with all required attributes
    frame = MagicMock(spec=AsyncFrame)
    frame.buffer = []
    frame.toplevel = False
    frame.rootlevel = False

    # Mock the methods called by visit_Block
    async_code_generator.blockvisit = MagicMock()
    async_code_generator.write = MagicMock()
    async_code_generator.writeline = MagicMock()
    async_code_generator.indent = MagicMock()
    async_code_generator.outdent = MagicMock()
    async_code_generator.choose_async = MagicMock(return_value="async ")
    async_code_generator.simple_write = MagicMock()
    async_code_generator.get_context_ref = MagicMock(return_value="context")
    async_code_generator.has_known_extends = False
    async_code_generator.extends_so_far = 0

    # Call visit_Block
    async_code_generator.visit_Block(block_node, frame)

    # Verify the method calls
    async_code_generator.blockvisit.assert_called_once_with(block_node.body, frame)


def test_visit_extends(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_Extends method."""
    # Create a mock Extends node
    extends_node = MagicMock(spec=nodes.Extends)
    extends_node.template = MagicMock(spec=nodes.Const)
    extends_node.template.value = "base.html"
    extends_node.lineno = 1

    # Create a mock frame
    frame = MagicMock(spec=AsyncFrame)
    frame.require_output_check = True  # Should be True to avoid CompilerExit
    frame.toplevel = True
    frame.rootlevel = True

    # Mock the methods called by visit_Extends
    async_code_generator.write = MagicMock()
    async_code_generator.visit = MagicMock()
    async_code_generator.writeline = MagicMock()
    async_code_generator.indent = MagicMock()
    async_code_generator.outdent = MagicMock()
    async_code_generator.extends_so_far = 0
    async_code_generator.has_known_extends = False

    # Call visit_Extends
    async_code_generator.visit_Extends(extends_node, frame)

    # Verify the method calls
    async_code_generator.visit.assert_called_once_with(extends_node.template, frame)
    assert async_code_generator.extends_so_far == 1
    assert async_code_generator.has_known_extends


def test_visit_include(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_Include method."""
    # Create a mock Include node
    include_node = MagicMock(spec=nodes.Include)
    include_node.template = MagicMock(spec=nodes.Const)
    include_node.template.value = "included.html"
    include_node.ignore_missing = False
    include_node.with_context = True
    include_node.lineno = 1

    # Create a mock frame
    frame = MagicMock(spec=AsyncFrame)
    frame.symbols = MagicMock()
    frame.symbols.dump_stores = MagicMock(return_value={})

    # Mock the methods called by visit_Include
    async_code_generator.write = MagicMock()
    async_code_generator.visit = MagicMock()
    async_code_generator.writeline = MagicMock()
    async_code_generator.indent = MagicMock()
    async_code_generator.outdent = MagicMock()
    async_code_generator.dump_local_context = MagicMock(return_value="{}")

    # Call visit_Include
    async_code_generator.visit_Include(include_node, frame)

    # Verify the method calls
    async_code_generator.visit.assert_called_once_with(include_node.template, frame)
    assert async_code_generator.write.call_count > 0


def test_func_code_generator(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the function code generator methods."""
    # Create a mock frame
    frame = MagicMock(spec=AsyncFrame)
    frame.is_async = True

    # Test the function code generator methods
    assert async_code_generator.func_code_generator(frame) == "async def"

    # Test with a non-async frame
    frame.is_async = False
    assert async_code_generator.func_code_generator(frame) == "def"


def test_return_buffer_contents(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the return_buffer_contents method."""
    # Create a mock frame
    frame = MagicMock(spec=AsyncFrame)
    frame.buffer = ["buffer_item1", "buffer_item2"]
    frame.is_async = True

    # Mock the writeline method
    async_code_generator.writeline = MagicMock()

    # Test the return_buffer_contents method
    async_code_generator.return_buffer_contents(frame)

    # Verify the writeline method was called
    async_code_generator.writeline.assert_called_once()


def test_visit_asyncfor(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_For method for async behavior."""
    # Create a mock For node with all required attributes
    asyncfor_node = MagicMock(spec=nodes.For)
    asyncfor_node.target = MagicMock(spec=nodes.Name)
    asyncfor_node.target.name = "item"
    asyncfor_node.iter = MagicMock(spec=nodes.Name)
    asyncfor_node.iter.name = "items"
    asyncfor_node.body = MagicMock(spec=nodes.Template)
    asyncfor_node.else_ = None
    asyncfor_node.recursive = False
    asyncfor_node.test = None

    # Create a mock frame with symbols
    frame = MagicMock(spec=AsyncFrame)
    frame.is_async = True
    frame.symbols = MagicMock()
    frame.symbols.store = MagicMock()

    # Mock the methods called by visit_For
    async_code_generator.write = MagicMock()
    async_code_generator.blockvisit = MagicMock()
    async_code_generator.writeline = MagicMock()
    async_code_generator.indent = MagicMock()
    async_code_generator.outdent = MagicMock()
    async_code_generator.temporary_identifier = MagicMock(return_value="tmp_var")

    # Mock iter_child_nodes method
    asyncfor_node.iter_child_nodes = MagicMock(return_value=[])

    # Patch the visit method to handle the target and iter
    with patch.object(async_code_generator, "visit") as mock_visit:
        # Call visit_For
        async_code_generator.visit_For(asyncfor_node, frame)

        # Verify the method calls
        assert mock_visit.call_count >= 2  # Called for target and iter
        assert async_code_generator.write.call_count > 0
        # blockvisit may be called multiple times, so use >= 1
        assert async_code_generator.blockvisit.call_count >= 1


def test_visit_asynccall(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_Call method with async=True."""
    # Create a mock Call node
    call_node = MagicMock(spec=nodes.Call)
    call_node.node = MagicMock(spec=nodes.Name)
    call_node.node.name = "async_function"
    call_node.args = []
    call_node.kwargs = []
    call_node.dyn_args = None
    call_node.dyn_kwargs = None
    call_node.lineno = 1

    # Create a mock frame with eval_ctx
    frame = MagicMock(spec=AsyncFrame)
    frame.is_async = True
    frame.eval_ctx = MagicMock()
    frame.eval_ctx.autoescape = False
    frame.symbols = MagicMock()
    frame.loop_frame = None
    frame.block_frame = None

    # Mock the methods called by visit_Call
    async_code_generator.write = MagicMock()
    async_code_generator.visit = MagicMock()

    # Call visit_Call
    async_code_generator.visit_Call(call_node, frame)

    # Verify the method calls
    assert async_code_generator.visit.call_count > 0
    assert async_code_generator.write.call_count > 0


def test_visit_asyncfilterblock(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_FilterBlock method with async=True."""
    # Create a mock FilterBlock node
    filterblock_node = MagicMock(spec=nodes.FilterBlock)
    filterblock_node.filter = MagicMock(spec=nodes.Filter)
    filterblock_node.filter.name = "filter_name"
    filterblock_node.filter.node = None
    filterblock_node.filter.args = []
    filterblock_node.filter.kwargs = []
    filterblock_node.filter.dyn_args = None
    filterblock_node.filter.dyn_kwargs = None
    filterblock_node.body = MagicMock(spec=nodes.Template)
    filterblock_node.lineno = 1

    # Create a mock frame
    frame = MagicMock(spec=AsyncFrame)
    frame.is_async = True
    frame.buffer = []
    frame.eval_ctx = MagicMock()
    frame.eval_ctx.autoescape = False

    # Mock the methods called by visit_FilterBlock
    async_code_generator.write = MagicMock()
    async_code_generator.blockvisit = MagicMock()
    async_code_generator.visit = MagicMock()
    async_code_generator.buffer = MagicMock()
    async_code_generator.enter_frame = MagicMock()
    async_code_generator.leave_frame = MagicMock()
    async_code_generator.start_write = MagicMock()
    async_code_generator.end_write = MagicMock()
    async_code_generator.filters = {"filter_name": "filter_name"}
    frame.inner = MagicMock(return_value=frame)
    frame.symbols = MagicMock()
    frame.symbols.analyze_node = MagicMock()
    frame.buffer = "test_buffer"

    # Call visit_FilterBlock
    async_code_generator.visit_FilterBlock(filterblock_node, frame)

    # Verify the method calls
    assert async_code_generator.blockvisit.call_count > 0
    assert async_code_generator.write.call_count > 0


def test_visit_asyncwith(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_With method with async=True."""
    # Create a mock With node
    with_node = MagicMock(spec=nodes.With)
    with_node.targets = [MagicMock(spec=nodes.Name)]
    with_node.values = [MagicMock(spec=nodes.Name)]
    with_node.body = MagicMock(spec=nodes.Template)

    # Create a mock frame that can create inner frames
    frame = MagicMock(spec=AsyncFrame)
    frame.is_async = True
    inner_frame = MagicMock(spec=AsyncFrame)
    inner_frame.symbols = MagicMock()
    inner_frame.symbols.analyze_node = MagicMock()
    frame.inner.return_value = inner_frame

    # Mock the methods called by visit_With
    async_code_generator.write = MagicMock()
    async_code_generator.blockvisit = MagicMock()
    async_code_generator.visit = MagicMock()
    async_code_generator.enter_frame = MagicMock()
    async_code_generator.leave_frame = MagicMock()
    async_code_generator.newline = MagicMock()

    # Call visit_With
    async_code_generator.visit_With(with_node, frame)

    # Verify the method calls
    assert async_code_generator.visit.call_count > 0
    assert async_code_generator.write.call_count > 0
    # The blockvisit should be called with the inner frame, not the original frame
    async_code_generator.blockvisit.assert_called_once_with(with_node.body, inner_frame)


def test_visit_asyncblock(async_code_generator: AsyncCodeGenerator) -> None:
    """Test the visit_Block method with async=True."""
    # Create a mock Block node
    block_node = MagicMock(spec=nodes.Block)
    block_node.name = "async_block"
    block_node.body = MagicMock(spec=nodes.Template)
    block_node.scoped = False
    block_node.required = False

    # Create a mock frame
    frame = MagicMock(spec=AsyncFrame)
    frame.is_async = True
    frame.buffer = []
    frame.toplevel = False
    frame.rootlevel = False

    # Mock the methods called by visit_Block
    async_code_generator.write = MagicMock()
    async_code_generator.blockvisit = MagicMock()
    async_code_generator.writeline = MagicMock()
    async_code_generator.indent = MagicMock()
    async_code_generator.outdent = MagicMock()
    async_code_generator.choose_async = MagicMock(return_value="async ")
    async_code_generator.simple_write = MagicMock()
    async_code_generator.get_context_ref = MagicMock(return_value="context")
    async_code_generator.derive_context = MagicMock(return_value="context")
    async_code_generator.blocks = {}
    async_code_generator.has_known_extends = False
    async_code_generator.extends_so_far = 0

    # Call visit_Block
    async_code_generator.visit_Block(block_node, frame)

    # Verify the method calls
    async_code_generator.blockvisit.assert_called_once_with(block_node.body, frame)
    # Check that writeline was called instead of write
    assert async_code_generator.writeline.call_count > 0
