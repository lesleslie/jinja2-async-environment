"""Tests for the DependencyResolver class to improve test coverage."""

from unittest.mock import MagicMock

from jinja2_async_environment.compiler_modules.dependencies import DependencyResolver


class TestDependencyResolver:
    """Test the DependencyResolver class."""

    def setup_mock_generator(self):
        """Set up a mock code generator for testing."""
        mock_generator = MagicMock()
        mock_generator.filters = {}
        mock_generator.tests = {}
        mock_generator.temporary_identifier.return_value = "temp_var"
        mock_generator.writeline = MagicMock()
        mock_generator.indent = MagicMock()
        mock_generator.outdent = MagicMock()
        return mock_generator

    def test_initialization(self):
        """Test initialization of DependencyResolver."""
        mock_generator = self.setup_mock_generator()
        resolver = DependencyResolver(mock_generator)

        assert resolver.code_generator is mock_generator

    def test_setup_filter_dependency_new_filter(self):
        """Test setting up a new filter dependency."""
        mock_generator = self.setup_mock_generator()
        resolver = DependencyResolver(mock_generator)

        # Initially, filters dict is empty
        assert len(mock_generator.filters) == 0

        # Setup a new filter dependency
        resolver.setup_filter_dependency("upper")

        # Verify the filter was added to the generator
        assert "upper" in mock_generator.filters
        assert mock_generator.filters["upper"] == "temp_var"

        # Verify the code generation calls
        mock_generator.writeline.assert_any_call("try:")
        mock_generator.writeline.assert_any_call("except KeyError:")
        mock_generator.writeline.assert_any_call("@internalcode")
        assert mock_generator.writeline.call_count >= 4  # at least the 4 expected lines

    def test_setup_filter_dependency_existing_filter(self):
        """Test setting up a filter dependency that already exists."""
        mock_generator = self.setup_mock_generator()
        mock_generator.filters = {"upper": "existing_var"}
        resolver = DependencyResolver(mock_generator)

        # Try to setup an existing filter
        resolver.setup_filter_dependency("upper")

        # Verify no new code was written (early return)
        mock_generator.writeline.assert_not_called()

    def test_setup_test_dependency_new_test(self):
        """Test setting up a new test dependency."""
        mock_generator = self.setup_mock_generator()
        resolver = DependencyResolver(mock_generator)

        # Initially, tests dict is empty
        assert len(mock_generator.tests) == 0

        # Setup a new test dependency
        resolver.setup_test_dependency("defined")

        # Verify the test was added to the generator
        assert "defined" in mock_generator.tests
        assert mock_generator.tests["defined"] == "temp_var"

        # Verify the code generation calls
        mock_generator.writeline.assert_any_call("try:")
        mock_generator.writeline.assert_any_call("except KeyError:")
        mock_generator.writeline.assert_any_call("@internalcode")
        assert mock_generator.writeline.call_count >= 4  # at least the 4 expected lines

    def test_setup_test_dependency_existing_test(self):
        """Test setting up a test dependency that already exists."""
        mock_generator = self.setup_mock_generator()
        mock_generator.tests = {"defined": "existing_var"}
        resolver = DependencyResolver(mock_generator)

        # Try to setup an existing test
        resolver.setup_test_dependency("defined")

        # Verify no new code was written (early return)
        mock_generator.writeline.assert_not_called()

    def test_filter_and_test_independence(self):
        """Test that filters and tests are managed independently."""
        mock_generator = self.setup_mock_generator()
        mock_generator.temporary_identifier.side_effect = ["filter_var", "test_var"]
        resolver = DependencyResolver(mock_generator)

        # Setup a filter
        resolver.setup_filter_dependency("upper")

        # Setup a test with the same name
        resolver.setup_test_dependency("upper")

        # Verify both exist independently
        assert "upper" in mock_generator.filters
        assert "upper" in mock_generator.tests
        assert mock_generator.filters["upper"] == "filter_var"
        assert mock_generator.tests["upper"] == "test_var"
        assert mock_generator.filters["upper"] != mock_generator.tests["upper"]
