# Crackerjack Style Rules

## Clean Code Philosophy (Foundation)

**EVERY LINE OF CODE IS A LIABILITY. The best code is no code.**

- **DRY (Don't Repeat Yourself)**: If you write it twice, you're doing it wrong
- **YAGNI (You Ain't Gonna Need It)**: Build only what's needed NOW
- **KISS (Keep It Simple, Stupid)**: Complexity is the enemy of maintainability
- **Less is More**: Prefer 10 lines that are clear over 100 that are clever
- **Code is Read 10x More Than Written**: Optimize for readability
- **Self-Documenting Code**: Code should explain itself; comments only for "why", not "what". Variable names should **ALWAYS** be clear and descriptive, even in inline map/filter functions.

## Code Quality & Style

- **Use Static Typing Everywhere**

  - Always include comprehensive type hints
  - Use modern typing syntax with the pipe operator (`|`) for unions instead of `Optional[T]`
  - Import typing as `import typing as t` and prefix all typing references with `t.`
  - Never import individual types directly from typing (e.g., avoid `from typing import List, Dict, Optional`)
  - Always use the `t.` prefix for all typing-related types
  - Use built-in collection types directly instead of typing equivalents:
    - Use `list[str]` instead of `t.List[str]`
    - Use `dict[str, int]` instead of `t.Dict[str, int]`
    - Use `tuple[int, ...]` instead of `t.Tuple[int, ...]`

- **Modern Python Features**

  - Target Python 3.13+ features and syntax
  - Use f-strings instead of other string formatting methods
  - Prefer `pathlib.Path` over `os.path` for file operations

- **Clean Code Architecture**

  - Write modular functions that do one thing well
  - **NO DOCSTRINGS**: Never add docstrings to any code - the codebase standard is to have no docstrings (they are automatically removed by the `-x` flag)
  - Avoid unnecessary line comments - use them sparingly only for complex logic
  - Use protocols (`t.Protocol`) instead of abstract base classes
  - Choose clear, descriptive variable and function names that make the code self-documenting (even in map/filter functions)
  - **Keep cognitive complexity ≤15 per function** - extract helper methods if needed (KISS principle)

- **Code Organization**

  - Group related functionality into well-defined classes
  - Use runtime-checkable protocols with `@t.runtime_checkable`
  - Prefer dataclasses for structured data
  - Use type checking with strict enforcement

- **Project Structure**

  - Structure projects with clear separation of concerns
  - Follow standard package layout conventions
  - Use [pyproject.toml](./pyproject.toml) for all configuration
  - **Modular Architecture**: Use protocol-based dependency injection
    - Core orchestration layer: `WorkflowOrchestrator`, `AsyncWorkflowOrchestrator`
    - Coordinator layer: `SessionCoordinator`, `PhaseCoordinator`
    - Domain managers: `HookManager`, `TestManager`, `PublishManager`
    - Infrastructure services: filesystem, git, config, security

## Tool Integration

- **Integrate with Quality Tools**

  - Configure code with Ruff for linting and formatting
  - Set up pre-commit hooks for consistent code quality
  - Use UV for dependency management

## Critical Error Prevention

**Bandit B108 (Hardcoded Temp Directory):**

```python
# NEVER do this - causes security warnings
config_path = "/tmp/test-config.yaml"

# ALWAYS use tempfile module
import tempfile

with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
    config_path = temp_file.name
```

**Refurb FURB184 (Return Statement Chaining):**

```python
# AVOID - unnecessary intermediate variable
def create_config() -> Config:
    generator = ConfigGenerator()
    return generator.create_config()


# PREFER - chained return statement
def create_config() -> Config:
    return ConfigGenerator().create_config()
```

**Pyright Protocol Compatibility:**

```python
# ALWAYS implement ALL protocol properties
class TestOptions(OptionsProtocol):
    # Missing properties cause type errors
    verbose: bool = False
    experimental_hooks: bool = False  # Don't forget new properties
    enable_pyrefly: bool = False
    enable_ty: bool = False
    compress_docs: bool = False
```

**Complexipy Complexity (>15):**

```python
# AVOID - high complexity method
def process_data(self, data: dict) -> Result:
    if condition1:
        if condition2:
            if condition3:
                pass  # ... many nested conditions >15 complexity


# PREFER - extracted helper methods
def process_data(self, data: dict) -> Result:
    if self._should_process(data):
        return self._handle_processing(data)
    return self._handle_error(data)


def _should_process(self, data: dict) -> bool:
    return condition1 and condition2 and condition3
```

- Implement pytest for testing with timeout handling

- **Use UV for Tool Execution**

  - Always use `uv run` to execute tools within the project's virtual environment
  - Run pytest with `uv run pytest` instead of calling pytest directly
  - Execute tools like pyright, ruff, and jinja2-async-environment through UV: `uv run pyright`
  - Ensures consistent tool versions and environment isolation

- **Pre-Commit Hook Configuration**

  - Enforce a comprehensive set of pre-commit hooks for quality control:
    - Pyright for static type checking
    - Ruff for linting and formatting
    - Vulture for detecting unused code
    - Creosote for identifying unused dependencies
    - Complexipy for code complexity analysis
    - Codespell for spell checking
    - Autotyping for type annotation
    - Refurb for Python code modernization
    - Bandit for security vulnerabilities
  - Run hooks with `uv run pre-commit run --all-files` during development
  - Configure hooks in `.pre-commit-config.yaml` with exact versions
  - Ensure all code passes pre-commit checks before submitting

- **Specific Tool Compliance Standards**

  - **Refurb (FURB Rules):**

    - **FURB109**: ALWAYS use tuples `()` instead of lists `[]` for `in` membership testing
    - **FURB120**: Never pass default values that match the function's default (e.g., `None` for optional parameters)
    - Use modern Python patterns and built-ins consistently

  - **Pyright Type Checking:**

    - **reportMissingParameterType**: ALL function parameters MUST have complete type annotations
    - **reportArgumentType**: Protocol implementations must include ALL required properties with correct types
    - Use explicit type annotations for all function parameters and return types

  - **Complexipy Code Complexity (KISS Enforcement):**

    - Keep cognitive complexity ≤15 per function/method
    - Break complex methods into 3-5 smaller helper functions with single responsibilities
    - Use descriptive function names that explain their purpose
    - Remember: complexity is the enemy of maintainability

  - **Bandit Security:**

    - Never use dangerous functions like `eval()`, `exec()`, or `subprocess.shell=True`
    - Use `secrets` module for cryptographic operations, never `random`
    - Always specify encoding when opening files

- **Automation Focus**

  - Automate repetitive tasks whenever possible
  - Create helpers for common development workflows
  - Implement consistent error handling and reporting

## Development Philosophy

Following our **Clean Code Philosophy** where every line of code is a liability:

- **Simplicity Over Cleverness** (KISS)

  - Choose obvious solutions over clever ones
  - Prefer explicit code over implicit magic
  - Write code that junior developers can understand

- **Build Only What's Needed** (YAGNI)

  - Implement current requirements, not future possibilities
  - Remove dead code immediately when discovered
  - Resist over-engineering and premature optimization

- **Eliminate Repetition** (DRY)

  - Extract common patterns into reusable functions
  - Create shared utilities for repeated operations
  - Use protocols and interfaces to reduce duplication

- **Consistency is Key**

  - Maintain uniform style across the entire codebase
  - Standardize import order and grouping
  - Keep a consistent approach to error handling

- **Reliability and Testing**

  - Write comprehensive tests using pytest
  - Add appropriate timeouts to prevent hanging tests
  - Use parallel test execution when appropriate
  - Never create files directly on the filesystem in tests
    - Always use `tempfile` module for temporary files and directories
    - Use pytest's `tmp_path` and `tmp_path_factory` fixtures
    - Clean up any generated resources after tests complete
    - Tests should be isolated and not affect the surrounding environment
    - Avoid hard-coded paths in tests that point to the real filesystem

- **Code Quality Validation**

  - Code should pass all quality checks when run through jinja2-async-environment
  - The ultimate goal is to run `python -m jinja2-async-environment -x -t` without any errors
  - This validates proper typing, formatting, linting, and test success
  - Consider code incomplete until it passes this validation

- **Error Handling**

  - Use structured exception handling with specific exception types
  - Provide meaningful error messages
  - Add appropriate error context for debugging

- **Rich Output**

  - Use the Rich library for console output
  - Provide clear status indicators for operations
  - Format output for readability

- **Opinionated Choices**

  - Enforce a single correct way to accomplish tasks
  - Remove unnecessary flexibility that could lead to inconsistency
  - Value clarity over brevity

## Additional Best Practices

- **Performance Considerations**

  - Use profiling tools to identify bottlenecks in critical code paths
  - Benchmark and compare alternative implementations for optimization
  - Favor readability over micro-optimizations except for demonstrated hot spots
  - Document any non-obvious optimizations with comments explaining the rationale

- **Python Version Strategy**

  - Target only the latest stable Python release (3.13+)
  - Adopt new language features as soon as they become available
  - Do not maintain backward compatibility with older Python versions
  - Regularly update codebases to take advantage of new language improvements
  - Plan to upgrade within weeks of a new Python release

- **Documentation Minimalism**

  - Keep documentation focused on "why" rather than "what" the code does
  - Document APIs at the module or class level rather than individual functions
  - Use type hints to replace most parameter documentation
  - Create examples for complex functionality instead of verbose explanations

- **Testing Philosophy**

  - Write tests for behavior, not implementation details
  - Focus on testing public interfaces rather than private functions
  - Use property-based testing for algorithmic code where appropriate
  - Separate unit tests, integration tests, and benchmarks
  - Aim for complete test coverage of critical paths but avoid test-for-test's-sake
  - Use asyncio exclusively for async testing; do not test with trio compatibility
  - Configure pytest with asyncio_mode="auto" for simpler async testing

- **Test Coverage Improvement (MANDATORY)**

  - **Target 42% milestone coverage**: Work toward 42% milestone (current: 21.6%, baseline: 19.6%). See [TEST_COVERAGE_IMPROVEMENTS.md](./docs/TEST_COVERAGE_IMPROVEMENTS.md).
  - **Always improve coverage incrementally** when working on projects with pytest coverage below the target
  - **Check coverage first**: Run `uv run pytest --cov=<package_name> --cov-report=term-missing` to see current status
  - **Target 2-5% improvement per session**: Add 1-3 focused tests that cover uncovered lines
  - **Prioritize easy wins**: Test simple functions, error paths, edge cases, and validation logic
  - **3-attempt rule**: If a test doesn't work after 3 debugging attempts, skip it and move on
  - **Time-boxed effort**: Spend maximum 10-15 minutes on coverage improvement per session
  - **Focus on low-hanging fruit**: Property getters, simple validation, string formatting, error handling
  - **Avoid complex coverage improvements**: Skip async operations, external integrations, and complex state management
  - **Write focused tests**: Each test should cover 1-3 lines of uncovered code
  - **Quality over quantity**: Tests should be simple, reliable, and fast (< 1 second each)
  - **Example incremental approach**:
    ```python
    # Target: Cover error handling in Options validation
    def test_options_invalid_bump_option():
        with pytest.raises(ValueError, match="Invalid bump option"):
            Options(publish="invalid")


    # Target: Cover string representation
    def test_bump_option_str():
        assert str(BumpOption.patch) == "patch"


    # Target: Cover edge case in validation
    def test_validate_empty_string():
        result = Options.validate_bump_options("")
        assert result == BumpOption.interactive
    ```

- **Dependency Management**

  - Keep external dependencies to a minimum
  - Pin exact versions in lockfiles but use range specifications in pyproject.toml
  - Regularly audit dependencies for security issues
  - Prefer standard library solutions when reasonable
  - Favor dependencies that support the latest Python version

- **Code Review Standards**

  - All code should be reviewed before merging
  - Automate style and formatting checks to focus reviews on substance
  - Look for edge cases and error handling in reviews
  - Ensure tests adequately cover the changes

- **Session Progress Tracking**

  - Progress tracking is now handled automatically by the MCP WebSocket server
  - Real-time progress monitoring available at `ws://localhost:8675`
  - Use `--resume-from` to continue interrupted sessions rather than starting over

## AI Agent Integration

- **AI Agent Iteration Workflow (CRITICAL)**

  - AI agent mode (`--ai-agent`) follows strict iteration protocol:
    1. **Fast Hooks** → Retry once if any fail (formatting fixes often cascade)
    1. **Collect ALL Test Failures** → Don't stop on first failure, gather complete list
    1. **Collect ALL Hook Issues** → Don't stop on first failure, gather complete list
    1. **Apply AI Fixes** → Process ALL collected issues in batch, then move to next iteration
  - **CRITICAL**: AI agent only advances to next iteration AFTER applying fixes
  - This ensures each iteration validates fixes from the previous iteration
  - Maximum 10 iterations to prevent infinite loops
  - AsyncWorkflowOrchestrator implements this logic for MCP server compatibility

- **MCP Server Integration**

  - Use standard orchestrator for MCP compatibility (not advanced orchestrator)
  - WebSocket progress reporting requires proper iteration boundaries
  - Real-time progress available at `ws://localhost:8675/ws/progress/{job_id}`
  - MCP tools: `execute_jinja2-async-environment`, `get_job_progress`, `get_comprehensive_status`

## AI Assistant Self-Maintenance

- **Quality Standards Maintenance**

  - AI assistants should update CLAUDE.md and RULES.md weekly or after pre-commit failures
  - Learn from new Refurb rules (FURB codes), Pyright errors (reportXxx), and Complexipy thresholds
  - Add newly discovered error patterns to documentation with code examples
  - Test all documentation updates by running `python -m jinja2-async-environment --comprehensive`
  - Prioritize frequently occurring error patterns as **CRITICAL** standards

- **Self-Learning Protocol**

  - When encountering new pre-commit failures, extract the error pattern and add to standards
  - Format new patterns with "Bad" and "Good" code examples
  - Update the "AI Code Generation Best Practices" checklist in CLAUDE.md
  - Ensure RULES.md stays synchronized with CLAUDE.md standards
  - Monitor tool version updates and incorporate new rules as they emerge
