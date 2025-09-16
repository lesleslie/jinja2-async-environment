"""Pre-compiled regex patterns for template compilation optimization."""

import re


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
