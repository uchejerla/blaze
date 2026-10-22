# Changelog

All notable changes to Blaze will be documented here.

---

## [0.1.1] — 2026-10-22

Correctness pass. Several programs were returning wrong answers rather than
failing loudly; this release fixes them and adds the first test suite.

### Fixed
- `return` / `break` / `continue` inside `try` were swallowed by the catch
  handler (`try: return 5` returned the handler's value)
- Assignment inside a function body no longer writes through to globals;
  each call gets its own frame, so functions cannot clobber caller variables
- `group_by` / `frequency` keep the original values as dict keys instead of
  stringifying them, so `group_by(xs, f)[30]` works
- `reduce(list, fn, init)` no longer ignores falsy `init` values on
  single-element lists, and reports empty-list-without-init as an error
- `percentile` interpolates linearly, so `percentile(data, 50) == median(data)`
  and values match NumPy; out-of-range percentiles are an error
- Dict comprehensions compute their keys: `{x: x*x for x in 1..3}` was
  producing `{x: 9}`
- Floats keep full precision when printed (`123456.789` no longer prints as
  `123457`), and `inf` / `-inf` / `nan` are printable
- `0/0` is `nan` instead of `-inf`
- `match` accepts single-line arms again: `match x | 1 -> "a" | _ -> "b"`

### Added
- Multi-line pipelines: a line starting with `|` continues the previous one,
  and newlines inside `(` `[` `{` are ignored
- `tests/` — 65 stdlib-only conformance tests (`python3 -m unittest discover -s tests`)
  covering README examples, builtins, error paths, the CLI and every example
- CI workflow running the suite on Python 3.8 / 3.11 / 3.12

### Changed
- `examples/` moved to the repository root (the README linked to it there);
  `tour.blz` rewritten and verified end to end
- README builtin table now lists only functions that exist (`flat`, `skip`
  rather than `flatten`, `drop`; removed `append`, `prepend`, `chars`, `num`)
- Documented outputs corrected (`median` 50.5, `corr` 0.9994,
  `linreg` `{slope: 2.02, intercept: 0.0}`)
- Removed the stale duplicate interpreter under `blaze-v0.1/` and the
  committed `.pyc`
- REPL continues on unbalanced brackets and trailing `|`
- `VERSION` 0.1.1

---

## [0.1.0] — 2026-08-05

### Added
- Pipeline-first syntax with `|` operator
- Arrow function definitions: `f(x) -> expr`
- Inline if-then-else expressions
- Range literals: `1..100`
- List and dict comprehensions
- Pattern matching: `match / | arms`
- String interpolation: `"value is {expr}"`
- Closures and higher-order functions
- Recursive functions with lexical scoping
- 60+ built-in functions (stats, list, string, math, type)
  - Statistics: `mean`, `std`, `median`, `corr`, `linreg`, `zscore`, `normalize`, `percentile`, `describe`
  - Lists: `sort`, `filter`, `map`, `reduce`, `take`, `drop`, `unique`, `reverse`, `flatten`, `chunk`, `zip`, `group_by`, `frequency`
  - Strings: `upper`, `lower`, `words`, `join`, `split`, `replace`, `trim`, `contains`
- Interactive REPL (`python3 blaze.py`)
- File runner (`python3 blaze.py script.blz`)
- One-liner eval (`python3 blaze.py -e "expr"`)
- `sort desc` / `sort asc` shorthand in pipes
- `print` statement (no parens required)
- Zero external dependencies — Python 3.8+ only

### Bug Fixes (during v0.1 development)
- `env.assign()` — for loop variable mutation now correctly walks the scope chain
- File runner no longer auto-prints return values of `for`/`while`/`if`/`match` blocks
- Range literals (`1..10`) now parse correctly after any primary expression (not just identifiers)
- `[1..10]` correctly returns a Range, not `List([Range(...)])`
- `sort(order="desc")` no longer conflicts with bare `sort desc` in pipe context
- `print "str"` (without parens) now parses correctly as a statement
- `match` expressions no longer require an INDENT block — works both inline and indented
- Fixed paren mismatch in stdlib `where` lambda

---

## Upcoming

### [0.3.0] — planned
- Table sugar: `select name, salary`, `group by dept`, `agg count`
  (today: `select_cols`, `group_by`, `count_where`)
- Standard library loader: `use "stats"` / `use "io"`

### [0.4.0] — planned
- `pip install blaze-lang`
- Proper package structure

### [0.5.0] — planned
- VSCode extension with `.blz` syntax highlighting
