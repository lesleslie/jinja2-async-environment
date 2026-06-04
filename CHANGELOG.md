# Changelog

## [0.19.2] - 2026-06-03

### Fixed

- 3-phase AsyncPackageLoader refactor

## [0.19.1] - 2026-06-03

### Fixed

- `AsyncPackageLoader.get_source_async`: read template files directly via `anyio.Path.read_bytes()` instead of routing through `self._loader.get_data(...)`. The previous call assumed the loader's path was a directory and only worked for zip-imported packages; for regular filesystem-installed packages the loader's path is the `__init__.py` file, so any `templates/...` lookup raised `FileNotFoundError`. `uptodate()` is now a synchronous `Path.stat()`-based closure matching upstream `jinja2.PackageLoader` semantics.
- A test-only backdoor in `_perform_initialization` that branched on the active test name was removed. Internal-only with no user-visible effect.
- `AsyncPackageLoader` now defends against path-traversal and symlink-escape attacks via a new `_is_safe_path` helper (mirrors `AsyncFileSystemLoader._is_safe_path`). The `..` containment check and the default `followlinks=False` together prevent an attacker-controlled template name from reading arbitrary files outside the package root. Exception wrapping was narrowed to `raise TemplateNotFound(name) from e` so absolute filesystem paths no longer leak into the user-facing error message.

### Changed

- `AsyncPackageLoader` now raises `ValueError` (not `RuntimeError`) when a package's `templates/` subdirectory is missing, with the message `"The {package_name!r} package was not installed in a way that PackageLoader understands."` This matches upstream `jinja2.PackageLoader`. Callers catching `RuntimeError` around construction or first `get_source_async` should switch to `ValueError` (or a broader catch).
- `AsyncPackageLoader.__init__` signature changed: the unused `searchpath` parameter was removed. Existing callers passing it positionally will need to drop the second argument (e.g. `AsyncPackageLoader("mypkg", "templates")` becomes `AsyncPackageLoader("mypkg")`).
- New keyword-only `followlinks: bool = False` parameter on `AsyncPackageLoader.__init__`. Set to `True` only for trusted packages that need legitimate in-tree symlinks; the default `False` is the safe setting.
- New `PackageLoaderError` exception class re-exported from `jinja2_async_environment.loaders` as the common base of `LoaderNotFound` and `PackageSpecNotFound`. Callers can now write a single `except PackageLoaderError` to catch both. The existing `LoaderNotFound` and `PackageSpecNotFound` names are preserved for backward compatibility.

## [0.19.0] - 2026-06-03

### Changed

- Jinja2-async-environment (quality: 68/100) - 2026-06-03 01:24:18

### Internal

- gitignore: Untrack session and coverage artifacts
- Update LICENSE copyright to 2026, standardize license field

## [0.18.7] - 2026-01-22

### Changed

- Update config, core, deps, docs

## [0.18.6] - 2025-11-26

### Changed

- Update config, core, deps, docs, tests

### Documentation

- config: Update 4 files

## [0.18.5] - 2025-10-26

### Fixed

- test: Update 28 files

## [0.18.4] - 2025-10-26

### Added

- test-coverage: Achieve 80% test coverage with comprehensive edge case tests

### Changed

- Jinja2-async-environment (quality: 68/100) - 2025-10-26 03:12:01

### Fixed

- config: Remove space in cov-fail-under pytest argument to fix validation error
- Implement proper template inheritance following base Jinja2 architecture
- Suppress zuban type checking warnings for jinja2 compiler imports

### Testing

- Comprehensive caching test coverage improvements (69% → 79%)
- core: Update 7 files

## [0.18.3] - 2025-09-18

### Testing

- config: Update 5 files

## [0.18.2] - 2025-09-18

### Documentation

- config: Update CHANGELOG, pyproject, uv

## [0.18.1] - 2025-09-17

### Testing

- config: Update 5 files

## [0.18.0] - 2025-09-17

### Changed

- Jinja2-async-environment (quality: 76/100) - 2025-09-17 13:15:23

### Documentation

- config: Update CHANGELOG, pyproject

## [0.17.1] - 2025-09-17

### Fixed

- test: Update 49 files

## [0.17.0] - 2025-09-17

### Changed

- Jinja2-async-environment (quality: 76/100) - 2025-09-16 09:11:42

## [0.14.0] - 2025-09-03

### Fixed

- Fixed constructor signature mismatches in loader classes
- Fixed method signature issues in loader classes
- Fixed missing import_module in loaders module
- Fixed get_source_async method calls in tests to include required environment parameter
- Fixed AsyncDictLoader searchpath initialization issues
- Fixed AsyncFunctionLoader constructor to properly handle single parameter
- Fixed AsyncChoiceLoader constructor to properly handle single parameter
- Resolved test suite failures from 61 failing tests to only 3 remaining edge cases

### Added

- Added comprehensive API reference documentation
- Enhanced README with improved examples and documentation
- Added development setup and testing guidelines

### Changed

- Updated loader constructors to maintain backward compatibility while fixing API inconsistencies
- Improved test coverage from ~41% to ~79% (significant progress toward the 80%+ floor)
- Enhanced documentation accuracy and completeness

## [0.13.0] - 2025-07-10

### Fixed

- Fixed async uptodate function support in template caching
- Fixed `RuntimeWarning: coroutine 'FileSystemLoader.get_source_async.<locals>.uptodate' was never awaited`
- Added proper async/await support for custom loader uptodate functions
- Enhanced `_is_template_up_to_date` method to use `inspect.iscoroutinefunction()` for proper async detection
- Fixed `_get_from_cache` method to properly await async uptodate checks
- Eliminated coroutine creation without awaiting by checking function type before calling

### Added

- Added comprehensive test suite for async uptodate function support
- Added tests for sync and async uptodate functions in template caching scenarios

## [0.12.0] - 2025-06-25

### Added

- Added comprehensive test coverage across all modules
- Added support for `AsyncDictLoader` and `AsyncFunctionLoader`
- Added `AsyncSandboxedEnvironment` for secure template execution in untrusted environments
- Enhanced async template rendering with `render_async()` method support
- Improved type safety and error handling

### Fixed

- Fixed `NameError: name 'escape' is not defined` error by adding the escape filter to the AsyncCodeGenerator
- Added import for `escape` from `markupsafe` in compiler.py
- Fixed AsyncFileSystemLoader to accept string paths and convert them to AsyncPath objects automatically
- Fixed refurb linting issues across the codebase
- Fixed cache key format issues in tests using weak references
- Fixed async mocking issues in test suites
- Resolved `TypeError: object MagicMock can't be used in 'await' expression` in tests

### Changed

- Updated dependency from `aiopath` to `anyio>=4.11.0` (current)
- **BREAKING CHANGE**: AsyncPath imports are now optional - all loaders accept string paths directly
- Improved code style and consistency with refurb suggestions
- Enhanced documentation with updated API usage examples showing string path support
- Updated Python requirement to 3.13+

### Improved

- **MAJOR PERFORMANCE BOOST**: Optimized `_async_yield_from` method by replacing exception handling with type detection
  - Eliminated try/catch overhead in hot path (347ms → ~1ms for large workloads)
  - ~300x performance improvement for async generator handling
  - Maintains full backward compatibility with async and sync generators
- Better async/await handling in environment caching
- More robust template loading error handling
- Enhanced performance through optimized async operations
