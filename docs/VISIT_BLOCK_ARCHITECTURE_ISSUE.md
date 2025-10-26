# visit_Block Architecture Issue

**Date**: 2025-10-26
**Session**: Extended debugging continuation
**Status**: Requires Upstream Architectural Redesign

## Executive Summary

Template inheritance in jinja2-async-environment fails because `visit_Block()` conflates two separate responsibilities that base Jinja2 keeps distinct:

1. **Block function DEFINITION** (should happen after root function)
1. **Block function CALLING** (should happen during template body processing)

This architectural difference prevents child templates from properly overriding parent blocks.

## Test Results

- **ACB Templates**: 71/74 passing (95.9%)
- **Inheritance tests**: 3 failing (return empty block content)
- **All other functionality**: Working correctly

## Root Cause Analysis

### Base Jinja2 Architecture (Correct)

In base Jinja2's `CodeGenerator.visit_Template`:

```python
# 1. Process root function with block CALLS
self.blockvisit(node.body, frame)  # visit_Block handles CALLING blocks
self.outdent()  # Exit root function

# 2. THEN define all block functions separately
for name, block in self.blocks.items():
    self.writeline(f"def block_{name}(context):")
    self.indent()
    # ... block body ...
    self.outdent()
```

**visit_Block in base Jinja2**: ONLY handles calling blocks

```python
def visit_Block(self, node, frame):
    # Call the block from context.blocks (allows overrides)
    self.writeline(f"gen = context.blocks[{node.name!r}][0]({context})")
    # ... iterate and yield ...
```

### jinja2-async-environment Architecture (Problematic)

In `AsyncCodeGenerator.visit_Block`: Does BOTH definition AND calling

```python
def visit_Block(self, node, frame):
    # DEFINES the block function
    self.writeline(f"async def block_{block_name}(context):")
    self.indent()
    # ... block body ...
    self.outdent()

    # Registers it
    self.writeline(f"blocks[{block_name!r}].append({block_func_name})")

    # AND calls it
    self.writeline(f"async for event in context.blocks[{block_name!r}][0]({context}):")
    # ... yield events ...
```

**Problem**: When a template with inheritance processes, visit_Block:

1. Defines the child's block function
1. Immediately tries to call it
1. But the block hasn't been registered to context.blocks yet
1. Results in empty block content

## Fixes Attempted

### 1. func() Method Fix ✅ **WORKING**

**File**: `codegen.py:107`

```python
# Before
def func(self, name: str) -> str:
    return f"def {name}"


# After
def func(self, name: str) -> str:
    return f"{self.choose_async()}def {name}"
```

**Impact**: Root functions now correctly generate as `async def root(...)` instead of `def root(...)`

### 2. frame.require_output_check Fix ✅ **WORKING**

**File**: `codegen.py:261`

```python
# Before
frame.require_output_check = False

# After
have_extends = node.find(nodes.Extends) is not None
frame.require_output_check = have_extends and not self.has_known_extends
```

**Impact**: Extends handling code now properly generated when templates use inheritance

### 3. Parent Template Iteration ⚠️ **PARTIALLY WORKING**

**File**: `codegen.py:264-279`
Added async parent template iteration code inside root function.

**Impact**:

- Templates ARE now async generators (correct function type)
- Parent iteration code IS generated
- But blocks return empty because visit_Block architecture is broken

### 4. context.blocks Changes ❌ **NOT HELPFUL**

Attempted to:

- Initialize context.blocks in root function
- Register blocks to context.blocks in visit_Block
- Use `context.blocks[name][0](context)` for calls

**Result**: Made situation more complex without fixing the core issue.

## Required Architectural Redesign

To fix template inheritance properly, jinja2-async-environment needs to:

### 1. Separate Block Definition from Block Calling

**Create new method for block definitions**:

```python
def _generate_block_functions(self, node):
    """Generate all block function definitions AFTER root function."""
    for block_node in self.blocks.values():
        block_name = block_node.name
        self.writeline(f"async def block_{block_name}(context):")
        self.indent()
        # ... generate block body ...
        self.outdent()
```

**Update visit_Block to ONLY handle calling**:

```python
def visit_Block(self, node, frame):
    """Call a block from context.blocks - allows inheritance overrides."""
    block_name = node.name
    context = self.get_context_ref()

    # ONLY call the block, don't define it
    self.writeline(f"async for event in context.blocks[{block_name!r}][0]({context}):")
    self.indent()
    self.writeline("yield event")
    self.outdent()
```

**Update generate() to call block generator**:

```python
def generate(self, node):
    # ... existing root function generation ...
    self.outdent()  # Exit root function

    # NOW generate all block functions
    self._generate_block_functions(node)

    # Register blocks dict
    blocks_kv = ", ".join(f"{name!r}: block_{name}" for name in self.blocks)
    self.writeline(f"blocks = {{{blocks_kv}}}")
```

### 2. Ensure Proper Block Registration

Blocks must be registered in BOTH places:

- **Template-level `blocks` dict**: For parent template lookup during extends
- **`context.blocks` dict**: For runtime override resolution

### 3. Handle Block Discovery

Like base Jinja2's visit_Template:

```python
# Find and store all blocks before processing
for block in node.find_all(nodes.Blocks):
    if block.name in self.blocks:
        self.fail(f"block {block.name!r} defined twice")
    self.blocks[block.name] = block
```

## Comparison: Current vs. Needed

### Current (Broken)

```
AsyncCodeGenerator.generate():
  └─ blockvisit(node.body)
      └─ visit_Block() called for each block:
          1. Defines block function
          2. Registers to blocks dict
          3. Calls block function
          └─ ❌ Blocks not yet in context, returns empty
```

### Needed (Like Base Jinja2)

```
AsyncCodeGenerator.generate():
  ├─ Discover all blocks first
  ├─ blockvisit(node.body)
  │   └─ visit_Block() - ONLY calls blocks from context.blocks
  ├─ Exit root function
  └─ _generate_block_functions()
      └─ Define all block functions AFTER root
      └─ ✅ Blocks available in context, inheritance works
```

## Impact Assessment

### ACB Project

- **Current**: 71/74 tests (95.9%)
- **With fix**: Would achieve 74/74 (100%)
- **Workaround**: ACB's render() method handles both coroutines and async generators gracefully

### FastBlocks

- **Impact**: Medium - affects \_render_standard() and \_render_block()
- **Workaround**: Can use same pattern as ACB

### starlette-async-jinja

- **Impact**: High - affects primary public API (TemplateResponse)
- **Workaround**: Apply root_render_func pattern like ACB

## Recommendations

### Immediate (This Session)

1. ✅ Keep func() method fix (line 107) - proven improvement
1. ✅ Keep frame.require_output_check fix (line 261) - enables extends
1. ❌ Revert context.blocks changes - adds complexity without benefit
1. ✅ Document findings for upstream

### Short-term (Next Session)

1. Apply ACB's workaround pattern to FastBlocks and starlette-async-jinja
1. Create upstream issue with jinja2-async-environment project
1. Include this analysis and proposed redesign

### Long-term (Upstream)

1. Implement architectural redesign in jinja2-async-environment
1. Separate block definition from block calling
1. Align with base Jinja2's two-phase approach
1. Add comprehensive inheritance tests

## Files Modified

### jinja2-async-environment

- `jinja2_async_environment/compiler_modules/codegen.py`: Multiple fixes attempted
  - Line 107: func() method ✅
  - Line 261: frame.require_output_check ✅
  - Lines 264-279: Parent iteration code ⚠️
  - Lines 241-249: context.blocks initialization (revert recommended)
  - Lines 326, 334: context.blocks usage in visit_Block (revert recommended)

### ACB

- `tests/adapters/templates/test_rendering.py:74-78`: Fixed undefined variable test ✅

## Lessons Learned

1. **Generated code ≠ Compiled behavior**: Source can look correct but behave wrong
1. **Architecture matters**: Conflating responsibilities creates subtle bugs
1. **Base implementation is a guide**: When extending Jinja2, follow its patterns
1. **Separation of concerns**: Definition vs. execution should be distinct phases
1. **Test the pattern**: jinja2-async-environment's own tests bypass render_async()

## Next Steps

1. User decision: Keep experimental changes or revert to minimal fix?
1. Update SESSION_SUMMARY_2025-10-26.md with visit_Block findings
1. Commit changes to jinja2-async-environment (either full or minimal)
1. Consider creating upstream PR with architectural redesign
1. Apply workarounds to FastBlocks and starlette-async-jinja

______________________________________________________________________

**Session Time**: ~4-5 hours of deep investigation
**Outcome**: Identified root cause requiring architectural redesign
**Test Improvement**: 70/74 → 71/74 (undefined variable fix)
**Inheritance**: Still broken, requires upstream redesign
