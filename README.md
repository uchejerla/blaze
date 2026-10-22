<div align="center">

# 🔥 Blaze

**Data analysis in one line.**

A pipeline-first language for data and analytics.
One file. Zero dependencies. Nothing to install.

[![tests](https://github.com/uchejerla/blaze/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/uchejerla/blaze/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-orange.svg)](#install)
[![Single file](https://img.shields.io/badge/install-one%20file-purple.svg)](#install)

**[Install](#install)** · **[Quick start](#quick-start)** · **[Language tour](#language-tour)** · **[Built-ins](#built-in-functions-100)** · **[Examples](#examples)** · **[Contributing](#contributing)**

</div>

---

```console
$ python3 blaze.py -e '[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum'
2418
```

That is the whole setup. No `pip install`, no virtualenv, no imports — download
`blaze.py` and run it.

## Why Blaze?

Data work is mostly a sequence of small transformations, but general-purpose
languages make you spell each step out and then read the result backwards.

```python
# Python
total = 0
for i in range(1, 100):
    if i % 3 == 0 or i % 5 == 0:
        total += i
print(total)
```

```blaze
# Blaze
[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum
```

The same idea applies at every size: strings, lists of records, CSVs, and
statistics all share one left-to-right pipeline.

- **Pipelines first.** Every value flows left to right through `|`. No
  intermediate variables, no nested calls to read backwards.
- **Nothing to install.** One `blaze.py`, standard library only, any Python 3.8+
  interpreter.
- **Batteries included.** 108 built-ins: statistics, linear regression, string
  handling, CSV tables, terminal histograms and scatter plots.
- **Tested documentation.** The conformance suite runs this README's examples
  and every file in `examples/`, so the docs cannot drift from the interpreter.

## Install

```bash
curl -O https://raw.githubusercontent.com/uchejerla/blaze/main/blaze.py
python3 blaze.py
```

Or clone the repository:

```bash
git clone https://github.com/uchejerla/blaze.git
cd blaze
python3 blaze.py
```

**Requirements:** Python 3.8 or newer. No external dependencies, ever.

## Quick start

```bash
python3 blaze.py              # Interactive REPL
python3 blaze.py script.blz   # Run a file
python3 blaze.py -e "expr"    # Evaluate one expression
```

The REPL keeps a session alive, continues multi-line pipelines, and prints
`help` for a syntax reference:

```console
$ python3 blaze.py

  ╔══════════════════════════════════════════════════════╗
  ║  🔥  Blaze v0.1.1  —  Pipeline-First Language          ║
  ║  Zero-setup · Zero-boilerplate · Maximum productivity ║
  ╚══════════════════════════════════════════════════════╝
  Type 'help' for a quick guide, 'exit' to quit.

blaze> data = [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]
  → [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]
blaze> data | sort | take(3)
  → [11, 12, 23]
blaze> exit
  Goodbye! 🔥
```

## Language tour

### Pipelines — chain everything with `|`

```blaze
# Filter, transform, aggregate — read it like a sentence
[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum
# → 2418

# Strings
"the quick brown fox" | words | map w -> upper(w) | join " "
# → "THE QUICK BROWN FOX"

# Data
data = [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]
data | sort desc | take(3)
# → [90, 89, 78]
```

Pipelines span lines: a line starting with `|` continues the previous one, as
does anything inside unclosed `(` `[` `{`.

```blaze
result = [1..20]
  | filter x -> x % 2 == 0
  | map x -> x * x
  | sum
# → 1540
```

### Functions — define and call inline

```blaze
double(x) -> x * 2
square(x) -> x * x

# Recursion
fib(n) -> if n <= 1 then n else fib(n-1) + fib(n-2)
[fib(n) for n in 0..12]
# → [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

# if-then-else is an expression, so this is a function body
abs_val(x) -> if x < 0 then -x else x
```

Closures capture their environment, which makes partially applied helpers
cheap:

```blaze
make_adder(n) -> x -> x + n

add5  = make_adder(5)
add10 = make_adder(10)

[add5(x) for x in 1..5]   # → [6, 7, 8, 9, 10]
[add10(x) for x in 1..5]  # → [11, 12, 13, 14, 15]
```

### Scope — locals stay local

Assignment inside a function body creates a local, so a helper cannot
accidentally overwrite your globals. Assignments in `if` / `for` / `while`
blocks do update the enclosing variable, so accumulators work as expected.

```blaze
counter = 0
bump() ->
  counter = counter + 1

bump()
counter                   # → 0
```

### Pattern matching

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

### Built-in statistics — no imports

```blaze
data = [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]

data | mean | round(2)                   # → 50.5
data | median                          # → 50.5
data | std | round(2)                  # → 30.19
data | sort | describe
# → {count: 10, mean: 50.5, std: 30.1892, min: 11, max: 90, median: 50.5}

# Correlation and least-squares fit
xs = [1, 2, 3, 4, 5]
ys = [2.1, 4.0, 5.9, 8.2, 10.1]
corr(xs, ys) | round(4)                # → 0.9994
linreg(xs, ys)                         # → {slope: 2.02, intercept: 0.0}
```

`std` and `var` are sample statistics (divide by n−1). `percentile`
interpolates linearly, so `percentile(data, 50) == median(data)`.

### Tables and CSV

`load` reads a CSV file into a table that prints itself in the terminal:

```console
$ cat people.csv
name,age,city
Ada,32,London
Linus,17,Helsinki
Grace,45,New York

$ python3 blaze.py -e 'load("people.csv") | where r -> r.age > 30 | select_cols("name", "city")'
name   city
─────  ────────
Ada    London
Grace  New York
```

A table is just a list of records, so the same pipeline works on data built in
code, on JSON, or on a CSV:

```blaze
people = table([
  {name: "Ada",   age: 32, city: "London"},
  {name: "Linus", age: 17, city: "Helsinki"},
  {name: "Grace", age: 45, city: "New York"}
])

people | where r -> r.age > 30 | select_cols("name", "city")
```

```
name   city
─────  ────────
Ada    London
Grace  New York
```

### Collections and strings

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

# Groups keep their native keys, so you can look them up
[1, 2, 3, 4, 5] | group_by x -> x % 2
# → {1: [1, 3, 5], 0: [2, 4]}
```

### Errors

A runtime failure stops the program with a one-line diagnostic, and
`try`/`catch` receives the message so you can recover instead:

```blaze
try:
  print [1, 2, 3][9]
catch (e):
  print "that index does not exist"
# → that index does not exist
```

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

## Examples

Runnable programs live in [`examples/`](examples/):

| File | What it shows |
|---|---|
| [`tour.blz`](examples/tour.blz) | The full language, end to end |
| [`data_analysis.blz`](examples/data_analysis.blz) | Statistics pipelines on real-ish data |
| [`euler1.blz`](examples/euler1.blz) | Project Euler solutions |
| [`fibonacci.blz`](examples/fibonacci.blz) | Recursion and comprehensions |
| [`hello.blz`](examples/hello.blz) | Hello, world |

Every example is executed by both the test suite and CI, so they are guaranteed
to run against the current interpreter.

## How it works

Blaze is a hand-written lexer, a recursive-descent parser and a tree-walking
interpreter in a single `blaze.py` of about 1,500 lines. There is no build step,
no generated code and no dependency graph — which is why the install is a
`curl` and the whole language fits in your head.

## Development

```bash
python3 -m unittest discover -s tests -v   # conformance suite, no dependencies
python3 blaze.py examples/tour.blz         # run a script
```

The suite covers the built-ins, the statistics (checked against Python's
`statistics` module), tables and CSV, the error paths, the CLI and the REPL,
and every file in `examples/`. Two tests guard the documentation: every
built-in named in this README must exist, and every linked example file must be
present. Documentation drift is a test failure, not a code review note.

See [CHANGELOG.md](CHANGELOG.md) for what changed and why.

## Roadmap

Shipped:

- [x] Core language — 108 built-ins, REPL, file runner, `-e`
- [x] CSV tables — `load("data.csv") | where r -> r.age > 30`
- [x] Terminal charts — `hist` and `scatter`
- [x] Conformance suite and CI on Python 3.8, 3.11 and 3.12

Planned:

- [ ] Table sugar — `select name, salary`, `group by dept`, `agg`
- [ ] Standard library loader — `use "stats"` / `use "io"`
- [ ] pip package — `pip install blaze-lang`
- [ ] VS Code extension with syntax highlighting

## Contributing

Blaze is in active early development, and contributions of every size are
welcome — bug reports, examples, built-ins, documentation fixes.

1. Fork the repository and create a branch.
2. Make your change, then run `python3 -m unittest discover -s tests`. The
   suite runs in about two seconds and needs no dependencies.
3. Open a pull request describing the problem first and the fix second.

If you add or change a built-in, update the table above — the tests will insist
on it.

## License

MIT © [Uday Shankar Chejerla](https://uchejerla.github.io)
