# Changelog

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
- Updated dependency from `aiopath` to `anyio>=4.9`
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
