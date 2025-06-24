# Changelog

## [Unreleased]

### Fixed
- Fixed `NameError: name 'escape' is not defined` error by adding the escape filter to the AsyncCodeGenerator
- Added import for `escape` from `markupsafe` in compiler.py
