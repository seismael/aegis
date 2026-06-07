# 🛡️ Aegis Project Health Scorecard

**Health Score: 69%**

## 📜 Active Rules
- **bp-use-pathlib**: Prefer pathlib over os.path for path manipulation.
- **bp-no-mutable-defaults**: Mutable default arguments cause surprising shared-state bugs.
- **bp-explicit-exceptions**: Bare except: clauses catch unexpected errors and should specify exception types.
- **bp-context-managers**: Use context managers (with statement) for resource handling.
- **bp-type-hints**: Functions with complex parameters should include type annotations.
- **bp-fstring-usage**: Prefer f-strings over str.format() or % formatting for string interpolation.
- **bp-list-comprehension**: Use list comprehensions over map/filter with lambda for clarity.
- **bp-walrus-appropriate**: Walrus operator (:=) should be used primarily in conditional expressions, not standalone.
- **bp-dataclass-usage**: Prefer dataclasses or Pydantic models over plain dicts for structured data.
- **bp-dunder-methods**: Classes should implement __str__ or __repr__ for debuggability.
- **bp-iterator-protocol**: Custom iterables should implement __iter__ or __next__, not rely solely on __getitem__.
- **bp-error-handling-depth**: Deeply nested try/except blocks indicate poor error handling design.
- **bp-no-hardcoded-strings**: String values used for configuration should be constants, enums, or environment variables, not inline literals.
- **bp-use-env-vars**: Configuration should be loaded from environment variables and .env files, not hardcoded at module level.
- **bp-no-magic-numbers**: Numeric literals used in business logic should be extracted as named constants or enum values.
- **bp-use-constants**: Repeated string or numeric literals used across multiple files should be centralized as constants or enums.
- **bp-avoid-globals**: Module-level mutable global state should be avoided; use dependency injection or context objects.
- **bp-use-logger**: Production code should use structured logging (logging or structlog) instead of print() for debugging output.
- **bp-guard-clauses**: Prefer early returns and guard clauses over deeply nested conditional blocks.
- **no-print**: No hardcoded print statements in domain logic
- **perf-repeated-computation**: Repeated len() calls inside loop bodies may indicate a cache opportunity.
- **perf-large-data-copies**: Full list slices [:] in loops create unnecessary O(n²) copies.
- **perf-sync-io-async**: Synchronous IO calls in async functions block the event loop.
- **perf-unbounded-append**: Repeated .append() calls may indicate a collection that should be pre-sized.
- **perf-string-concat**: Use str.join() instead of += for string concatenation in loops.
- **perf-n-plus-1**: Database queries inside loops indicate potential N+1 query patterns.

## ⚠️ Exceptions (Technical Debt)
The following rules have baseline exceptions (suppressed violations):

- **no-print**: 20 baselined locations
