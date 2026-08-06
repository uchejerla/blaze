# Changelog

All notable changes to Blaze will be documented here.

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

### [0.2.0] — planned
- Table / CSV support: `load("data.csv") | where col > val | select col1, col2`
- Multi-param lambdas: `(x, y) -> x + y`

### [0.3.0] — planned
- Standard library loader: `use "stats"` / `use "io"`
- File I/O: `read("file.txt")`, `write("out.txt", data)`

### [0.4.0] — planned
- `pip install blaze-lang`
- Proper package structure

### [0.5.0] — planned
- VSCode extension with `.blz` syntax highlighting
