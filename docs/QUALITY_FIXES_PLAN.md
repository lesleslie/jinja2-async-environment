# Quality Fixes Implementation Plan

## 1. Type Errors (Critical - Blocking Compilation)

### Issue: Item "None" has no attribute errors

**Files**: `compiler_old.py:978-983`, `compiler_modules/codegen.py:778-783`

**Root Cause**: `_PassArg = getattr(jinja2.compiler, "_PassArg", None)` can return None, but code assumes it has attributes.

**Fix**: Add proper None checks before accessing attributes.

## 2. Refurb Code Improvements (22 issues)

### Categories:

1. **FURB109**: Replace `in [x, y, z]` with `in (x, y, z)` for performance
1. **FURB107**: Use `with suppress(Exception)` instead of try/except pass
1. **FURB117**: Use operator.itemgetter instead of lambda
1. **FURB113**: Use list comprehensions instead of append loops
1. **FURB157**: Use dict comprehensions
1. **FURB124**: Use os.path.getmtime directly
1. **FURB148**: Use f-strings

## 3. Complexity Issues (5 functions exceed limit)

### Functions exceeding complexity 13:

1. **AsyncFileSystemLoader::list_templates** (18) - Split into helper methods
1. **AsyncCodeGenerator::pop_as...** methods (19 each) - Extract conditional logic
1. **AsyncFunctionLoader::get_source** (22) - Split validation and processing
1. **AsyncBaseLoader::__init__** (23) - Extract initialization logic

## Implementation Order

1. **Phase 1**: Fix type errors (blocking issue)
1. **Phase 2**: Apply refurb improvements (code quality)
1. **Phase 3**: Reduce complexity (maintainability)

## Testing Strategy

- Run tests after each phase to ensure no regressions
- Use crackerjack validation after all fixes
- Document any performance improvements
