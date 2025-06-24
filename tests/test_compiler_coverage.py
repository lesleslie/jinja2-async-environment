import typing as t
from unittest.mock import MagicMock

import pytest
from jinja2 import nodes
from jinja2.compiler import CodeGenerator
from jinja2_async_environment.compiler import AsyncCodeGenerator
from jinja2_async_environment.environment import AsyncEnvironment


def create_mock_node(node_type: type[nodes.Node], **kwargs: t.Any) -> t.Any:
    """Create a mock node of the specified type."""
    mock_node = MagicMock(spec=node_type)
    for key, value in kwargs.items():
        setattr(mock_node, key, value)
    return mock_node


@pytest.fixture
def async_code_generator() -> AsyncCodeGenerator:
    """Create an AsyncCodeGenerator instance for testing."""
    env = AsyncEnvironment()
    return AsyncCodeGenerator(env, "<string>", "test.py")


def test_async_code_generator_init() -> None:
    """Test initialization of AsyncCodeGenerator."""
    env = AsyncEnvironment()
    generator = AsyncCodeGenerator(env, "<string>", "test.py")

    assert generator.environment == env
    assert generator.name == "<string>"
    assert generator.filename == "test.py"
    assert generator.stream is not None


def test_async_code_generator_inheritance() -> None:
    """Test that AsyncCodeGenerator inherits from CodeGenerator."""
    env = AsyncEnvironment()
    generator = AsyncCodeGenerator(env, "<string>", "test.py")

    assert isinstance(generator, CodeGenerator)


def test_visit_asyncfor(async_code_generator: AsyncCodeGenerator) -> None:
    """Test visit_For method for async behavior."""
    # Create a mock For node (Jinja2 doesn't have AsyncFor)
    target = create_mock_node(nodes.Name, name="item")
    iter_node = create_mock_node(nodes.Name, name="items")
    body = [
        create_mock_node(
            nodes.Output, nodes=[create_mock_node(nodes.Name, name="item")]
        )
    ]
    else_body = []

    for_node = create_mock_node(
        nodes.For,
        target=target,
        iter=iter_node,
        body=body,
        else_=else_body,
        recursive=False,
        test=None,
    )

    # Mock the necessary methods
    async_code_generator.visit = MagicMock()
    async_code_generator.write = MagicMock()
    async_code_generator.blockvisit = MagicMock()

    # Call the method
    frame = MagicMock()
    frame.symbols = MagicMock()
    frame.symbols.store = MagicMock()
    async_code_generator.writeline = MagicMock()
    async_code_generator.temporary_identifier = MagicMock(return_value="tmp_var")
    async_code_generator.indent = MagicMock()
    async_code_generator.outdent = MagicMock()

    async_code_generator.visit_For(for_node, frame)

    # Verify the method calls
    assert async_code_generator.write.call_count > 0
    assert async_code_generator.blockvisit.call_count > 0


def test_visit_asynccall(async_code_generator: AsyncCodeGenerator) -> None:
    """Test visit_Call method for async behavior."""
    # Create a mock Call node
    node = create_mock_node(
        nodes.Call,
        node=create_mock_node(nodes.Name, name="async_function"),
        args=[create_mock_node(nodes.Const, value="arg1")],
        kwargs=[],
        dyn_args=None,
        dyn_kwargs=None,
    )

    # Mock the necessary methods
    async_code_generator.visit = MagicMock()
    async_code_generator.write = MagicMock()

    # Call the method with a frame
    frame = MagicMock()
    async_code_generator.visit_Call(node, frame)

    # Verify the method calls
    assert async_code_generator.visit.call_count > 0
    assert async_code_generator.write.call_count > 0
