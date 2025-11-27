# Immediate Action Plan for Fixing Test Failures

## Priority 1: Fix Constructor Signature Issues

### 1. AsyncFunctionLoader Constructor Fixes

**Files to Update**:

1. `tests/test_benchmarks.py` line 211
1. `tests/test_e2e.py` line 76
1. `tests/test_function_loader.py` lines 66, 73, 79, 90, 162
1. `tests/test_loaders_coverage.py` lines 105, 125, 198, 226
1. `tests/test_loader_adapter.py` lines 108, 135

**Change Required**:

```python
# BEFORE (incorrect):
loader = AsyncFunctionLoader(load_func, AsyncPath("/templates"))

# AFTER (correct):
loader = AsyncFunctionLoader(load_func)
```

### 2. AsyncChoiceLoader Constructor Fixes

**Files to Update**:

1. `tests/test_benchmarks.py` line 230
1. `tests/test_e2e.py` line 76
1. `tests/test_choice_loader.py` line 70
1. `tests/test_loaders_coverage.py` lines 105, 198
1. `tests/test_loader_adapter.py` line 135

**Change Required**:

```python
# BEFORE (incorrect):
loader = AsyncChoiceLoader(loaders, AsyncPath("/templates"))

# AFTER (correct):
loader = AsyncChoiceLoader(loaders)
```

## Priority 2: Fix Method Signature Issues

### 1. get_source_async Method Fixes

**Files to Update**:

1. `tests/test_dict_loader.py` lines 40, 51, 57, 89
1. `tests/test_loaders.py` lines 36, 64, 83
1. `tests/test_loader_adapter.py` lines 31, 78

**Change Required**:

```python
# BEFORE (incorrect):
await loader.get_source_async(AsyncPath("template.html"))

# AFTER (correct):
await loader.get_source_async(environment, "template.html")
```

### 2. Environment Parameter Handling Fixes

**Files to Update**:

1. `tests/test_loaders.py` lines 64, 83
1. `tests/test_loader_adapter.py` lines 31, 78

**Change Required**:

```python
# BEFORE (incorrect):
await loader.get_source_async(template_name)

# AFTER (correct):
await loader.get_source_async(environment, template_name)
```

## Priority 3: Fix Import Issues

### 1. AsyncPackageLoader Import Fixes

**Files to Update**:

1. `jinja2_async_environment/loaders/__init__.py`
1. `tests/test_package_loader.py` lines 53, 76, 90, 115, 187, 288, 334
1. `tests/test_loaders_coverage.py` line 91

**Change Required**:
Add import_module to loaders module:

```python
# In jinja2_async_environment/loaders/__init__.py
from importlib import import_module
```

## Priority 4: Fix Initialization Issues

### 1. AsyncDictLoader Searchpath Fixes

**Files to Update**:

1. `tests/test_dict_loader.py` line 33

**Change Required**:

```python
# BEFORE (incorrect assertion):
assert len(loader.searchpath) == 1

# AFTER (correct approach):
# Either fix the loader implementation or update the test expectation
# The loader should properly initialize searchpath
```

## Implementation Order

### Step 1: Fix Import Issues (15 minutes)

1. Add import_module to loaders module

### Step 2: Fix Constructor Signatures (1 hour)

1. Update AsyncFunctionLoader constructor calls in all test files
1. Update AsyncChoiceLoader constructor calls in all test files

### Step 3: Fix Method Signatures (1 hour)

1. Update get_source_async method calls to include environment and name parameters
1. Fix environment parameter handling in loader method calls

### Step 4: Fix Initialization Issues (30 minutes)

1. Fix AsyncDictLoader searchpath initialization or test expectations

## Verification Steps

### After Each Fix:

1. Run the specific failing test to verify it passes
1. Run related tests to ensure no regressions

### After All Fixes:

1. Run entire test suite: `pytest`
1. Check coverage: `pytest --cov=jinja2_async_environment`
1. Run benchmarks: `pytest --benchmark-only`

## Common Patterns to Fix

### Pattern 1: Constructor Calls

```python
# WRONG:
AsyncFunctionLoader(func, path)

# CORRECT:
AsyncFunctionLoader(func)
```

### Pattern 2: Method Calls

```python
# WRONG:
await loader.get_source_async(name)

# CORRECT:
await loader.get_source_async(environment, name)
```

### Pattern 3: Environment Parameter

```python
# WRONG:
await loader.method(template_name)

# CORRECT:
await loader.method(environment, template_name)
```

## Testing Verification Commands

```bash
# Test individual fixed components
pytest tests/test_function_loader.py
pytest tests/test_choice_loader.py
pytest tests/test_dict_loader.py

# Test loaders
pytest tests/test_loaders.py
pytest tests/test_loaders_coverage.py

# Test packages
pytest tests/test_package_loader.py

# Test benchmarks (after fixes)
pytest tests/test_benchmarks.py

# Test end-to-end
pytest tests/test_e2e.py

# Run full test suite
pytest

# Check coverage
pytest --cov=jinja2_async_environment --cov-report=term-missing
```

## Expected Outcomes

### After Fixes:

- **Failed Tests**: Should reduce from 61 to 0-5
- **Error Tests**: Should reduce from 17 to 0
- **Passed Tests**: Should increase from 251 to 300+
- **Coverage**: Should improve from 41% to 50%+

### Next Steps:

1. Once immediate fixes are complete, focus on coverage improvement
1. Add missing unit tests for uncovered code paths
1. Implement performance benchmarking tests
1. Add integration and end-to-end tests
