# Changelog

## [0.12.0] - 2024-12-XX

### Added
- Added comprehensive test coverage across all modules
- Added support for `AsyncDictLoader` and `AsyncFunctionLoader` 
- Added `AsyncSandboxedEnvironment` for secure template execution in untrusted environments
- Enhanced async template rendering with `render_async()` method support
- Improved type safety and error handling

### Fixed
- Fixed `NameError: name 'escape' is not defined` error by adding the escape filter to the AsyncCodeGenerator
- Added import for `escape` from `markupsafe` in compiler.py
- Fixed refurb linting issues across the codebase
- Fixed cache key format issues in tests using weak references
- Fixed async mocking issues in test suites
- Resolved `TypeError: object MagicMock can't be used in 'await' expression` in tests

### Changed
- Updated dependency from `aiopath` to `anyio>=4.9`
- Improved code style and consistency with refurb suggestions
- Enhanced documentation with correct API usage examples
- Updated Python requirement to 3.13+

### Improved
- Better async/await handling in environment caching
- More robust template loading error handling  
- Enhanced performance through optimized async operations
