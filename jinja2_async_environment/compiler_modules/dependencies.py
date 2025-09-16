"""Dependency resolution for template filters and tests."""

import typing as t

if t.TYPE_CHECKING:
    from .codegen import AsyncCodeGenerator


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
