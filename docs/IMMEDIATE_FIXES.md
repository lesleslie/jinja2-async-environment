# Immediate Fixes for Test Failures

## 1. Fix AsyncFunctionLoader Constructor Signature

**Issue**: Tests are passing 2 parameters but constructor only expects 1.

**Current constructor**:

```python
def __init__(self, load_func: LoaderFunction | AsyncLoaderFunction) -> None:
```

**Fix needed**: Update tests to only pass the load_func parameter.

**Files to fix**:

- tests/test_benchmarks.py line 211
- tests/test_e2e.py line 76
- tests/test_function_loader.py lines 66, 73, 79, 90, 162
- tests/test_loaders_coverage.py lines 105, 125, 198, 226
- tests/test_loader_adapter.py lines 108, 135

## 2. Fix AsyncChoiceLoader Constructor Signature

**Issue**: Tests are passing 2 parameters but constructor only expects 1.

**Current constructor**:

```python
def __init__(self, loaders: t.Sequence[AsyncLoaderProtocol]) -> None:
```

**Fix needed**: Update tests to only pass the loaders parameter.

**Files to fix**:

- tests/test_benchmarks.py line 230
- tests/test_e2e.py line 76
- tests/test_choice_loader.py line 70
- tests/test_loaders_coverage.py lines 105, 198
- tests/test_loader_adapter.py line 135

## 3. Fix get_source_async Method Signatures

**Issue**: Methods are missing required `name` parameter.

**Current base method signature**:

```python
async def get_source_async(self, environment: "AsyncEnvironment", name: str) -> SourceType:
```

**Issues found**:

- AsyncBaseLoader.get_source_async missing `name` parameter in tests
- AsyncDictLoader.get_source_async missing `name` parameter in tests

**Files to fix**:

- tests/test_dict_loader.py lines 40, 51, 57, 89
- tests/test_loaders.py lines 36, 64, 83
- tests/test_loader_adapter.py lines 31, 78

## 4. Fix Environment Parameter Handling

**Issue**: Some tests not properly passing environment parameter to loader methods.

**Files to fix**:

- tests/test_loaders.py lines 64, 83
- tests/test_loader_adapter.py lines 31, 78

## 5. Fix AsyncPackageLoader Import Issues

**Issue**: Missing import_module in loaders module.

**Files to fix**:

- jinja2_async_environment/loaders/__init__.py
- tests/test_package_loader.py lines 53, 76, 90, 115, 187, 288, 334
- tests/test_loaders_coverage.py line 91

## 6. Fix AsyncDictLoader Searchpath Issues

**Issue**: Searchpath initialization problems.

**Files to fix**:

- tests/test_dict_loader.py line 33

## Priority Fix Order

1. **High Priority** (Blocking most tests):

   - Fix AsyncFunctionLoader constructor calls
   - Fix AsyncChoiceLoader constructor calls
   - Fix get_source_async method calls
   - Fix environment parameter handling

1. **Medium Priority**:

   - Fix AsyncPackageLoader import issues
   - Fix AsyncDictLoader searchpath issues

1. **Low Priority**:

   - Update test assertions that expect specific error messages
   - Fix any remaining mock-related issues
