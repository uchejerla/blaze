# 🔥 Blaze

**Pipeline-first programming language for data & analytics.**

```
python3 blaze.py -e "[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum"
# → 2418
```

[![tests](https://github.com/uchejerla/blaze/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/uchejerla/blaze/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-orange.svg)]()
[![Single file](https://img.shields.io/badge/install-one%20file-purple.svg)]()

---

## Why Blaze?

Data work in Python involves a lot of ceremony — imports, loops, intermediate variables, method chaining that reads right-to-left. Blaze makes the common case one line.

| Task | Python | Blaze |
|---|---|---|
| Sum multiples of 3 or 5 below 100 | 5 lines | 1 line |
| Compute mean, std, and top-3 of a list | 5 lines | 4 lines |
| Uppercase every word in a string | 2 lines | 1 line |
| Word frequency count | 2 lines (+ import) | 1 line |
| Fibonacci (first 13) | 4 lines | 2 lines |

---

## Install

No pip. No setup. One file.

```bash
curl -O https://raw.githubusercontent.com/uchejerla/blaze/main/blaze.py
python3 blaze.py
```

Or clone:

```bash
git clone https://github.com/uchejerla/blaze.git
cd blaze
python3 blaze.py
```

**Requirements:** Python 3.8+ · No external dependencies

---

## Quick Start

```bash
python3 blaze.py              # Interactive REPL
python3 blaze.py script.blz  # Run a file
python3 blaze.py -e "expr"   # One-liner
```

---

## Language Highlights

### Pipes — chain everything with `|`

```blaze
# Filter, transform, aggregate — left to right
[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum
# → 2418

# String pipelines
"the quick brown fox" | words | map w -> upper(w) | join " "
# → "THE QUICK BROWN FOX"

# Data analysis
data = [23, 45, 12, 67, 34, 89, 56, 78]
data | sort desc | take(3)
# → [89, 78, 67]
```

### Arrow Functions — define and call inline

```blaze
double(x) -> x * 2
square(x) -> x * x

# Recursive
fib(n) -> if n <= 1 then n else fib(n-1) + fib(n-2)
[fib(n) for n in 0..12]
# → [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

# If-then-else is an expression
abs_val(x) -> if x < 0 then -x else x
```

### Closures & Higher-Order Functions

```blaze
make_adder(n) -> x -> x + n

add5  = make_adder(5)
add10 = make_adder(10)

[add5(x) for x in 1..5]   # → [6, 7, 8, 9, 10]
[add10(x) for x in 1..5]  # → [11, 12, 13, 14, 15]
```

### Scope

Assignment inside a function body creates a local, so functions cannot
accidentally overwrite globals:

```blaze
counter = 0
bump() ->
  counter = counter + 1   # a local `counter` — the global stays 0

bump()
counter                   # → 0
```

Assignments in `if` / `for` / `while` blocks update the enclosing variable, so
accumulators work as you would expect.

### Multi-line pipelines

A line that starts with `|` continues the previous line, as does anything
inside unclosed `(` `[` `{`:

```blaze
result = [1..20]
  | filter x -> x % 2 == 0
  | map x -> x * x
  | sum
# → 1540
```

### Built-in Statistics — no imports

```blaze
data = [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]

print "Mean:      {data | mean | round(2)}"     # → 50.5
print "Std Dev:   {data | std | round(2)}"      # → 30.19
print "Median:    {data | median}"              # → 50.5
print "Top 3:     {data | sort desc | take(3)}" # → [90, 89, 78]

# Correlation
xs = [1, 2, 3, 4, 5]
ys = [2.1, 4.0, 5.9, 8.2, 10.1]
corr(xs, ys) | round(4)   # → 0.9994

# Linear regression
linreg(xs, ys)  # → {slope: 2.02, intercept: 0.0}

# `std` and `var` are sample statistics (divide by n-1);
# `percentile` interpolates linearly, so percentile(d, 50) == median(d).
```

### Range Literals

```blaze
1..10           # → [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
[1..5] | sum    # → 15
[x*x for x in 1..10 if x % 2 == 0]  # → [4, 16, 36, 64, 100]
```

### String Interpolation

```blaze
name = "Blaze"
n    = 42
"Hello from {name}! The answer is {n * 2}."
# → "Hello from Blaze! The answer is 84."
```

### Pattern Matching

```blaze
grade(score) ->
  match score
  | >= 90 -> "A"
  | >= 80 -> "B"
  | >= 70 -> "C"
  | >= 60 -> "D"
  | _     -> "F"

[grade(s) for s in [95, 83, 74, 55]]
# → ["A", "B", "C", "F"]
```

### Collections

```blaze
# Lists
nums = [3, 1, 4, 1, 5, 9, 2, 6]
nums | sort | unique        # → [1, 2, 3, 4, 5, 6, 9]

# Dicts
person = {name: "Alice", age: 30}
person.name                 # → "Alice"

# Word frequency
"blaze is fast blaze is fun" | words | frequency
# → {blaze: 2, is: 2, fast: 1, fun: 1}
```

---

## Built-in Functions (100+)

| Category | Functions |
|---|---|
| Math | `sum` `min` `max` `abs` `sqrt` `pow` `floor` `ceil` `round` `log` `exp` `sin` `cos` `tan` `clamp` `lerp` |
| Stats | `mean` `median` `std` `var` `corr` `zscore` `linreg` `normalize` `percentile` `describe` `hist` `scatter` |
| Lists | `sort` `sort_by` `filter` `map` `reduce` `take` `skip` `first` `last` `unique` `reverse` `flat` `count` `len` `chunk` `zip` `group_by` `frequency` `partition` `cumsum` `diff` `find` `any` `all` |
| Strings | `upper` `lower` `words` `lines` `trim` `ltrim` `rtrim` `split` `join` `replace` `contains` `starts_with` `ends_with` `pad_left` `pad_right` `repeat` |
| Tables | `table` `load` `cols` `rows` `head` `tail` `where` `select_cols` `describe` |
| Type | `str` `int` `float` `bool` `list` `type` |
| I/O | `print` `show` `input` `read_file` `write_file` `load_json` `save_json` |

`group_by` and `frequency` keep the original values as keys, so
`group_by(users, u -> u.age)[30]` works as expected.

---

## Examples

See the [`examples/`](examples/) directory:

- [`tour.blz`](examples/tour.blz) — full language tour
- [`euler1.blz`](examples/euler1.blz) — Project Euler solutions
- [`data_analysis.blz`](examples/data_analysis.blz) — statistics & data analysis
- [`fibonacci.blz`](examples/fibonacci.blz) — recursion and comprehensions
- [`hello.blz`](examples/hello.blz) — hello world

Every example is executed by the test suite, so they are guaranteed to run.

---

## Development

```bash
python3 -m unittest discover -s tests -v   # 65 conformance tests, no dependencies
```

The suite covers every README example, the builtins, the error paths and each
file in `examples/`. It also fails if the README documents a function that does
not exist — documentation drift is a test failure, not a code review note.

---

## Roadmap

- [x] `v0.1` — Core language, 100+ builtins, REPL, file runner, `-e`
- [x] `v0.2` — CSV tables: `load("data.csv") | where r -> r.age > 30`
- [ ] `v0.3` — Table sugar: `select name, salary`, `group by dept`, `agg`
- [ ] `v0.3` — Standard library loader: `use "stats"` / `use "io"`
- [ ] `v0.4` — pip package: `pip install blaze-lang`
- [ ] `v0.5` — VSCode extension with syntax highlighting

---

## Contributing

Blaze is in active early development. Open an issue or PR — all welcome.

---

## License

MIT © [Uday Shankar Chejerla](https://uchejerla.github.io)
