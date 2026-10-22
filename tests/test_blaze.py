#!/usr/bin/env python3
"""
Conformance tests for the Blaze interpreter.

Zero dependencies — standard library only, like the language itself.

    python3 -m unittest discover -s tests -v
"""

import contextlib
import importlib.util
import io
import pathlib
import re
import statistics
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLAZE_PY = ROOT / "blaze.py"

_spec = importlib.util.spec_from_file_location("blaze_under_test", BLAZE_PY)
blaze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(blaze)


# ── helpers ──────────────────────────────────────────────────────

def evaluate(src):
    """Run Blaze source in a fresh interpreter and return the raw value."""
    return blaze.Interpreter().run(src)


def show(src):
    """Run Blaze source and return the value as Blaze would print it.

    Anything the program itself prints is discarded; use output() for that.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return blaze.br(evaluate(src))


def output(src):
    """Run Blaze source and capture everything it prints."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        blaze.Interpreter().run(src)
    return buf.getvalue()


def cli(*args, stdin=None):
    """Run blaze.py as the user would."""
    return subprocess.run(
        [sys.executable, str(BLAZE_PY), *args],
        capture_output=True, text=True, input=stdin, timeout=120,
    )


def stdlib():
    """Public names a program can use without defining anything."""
    env = blaze.Interpreter().genv
    return {k for k in env.v if not k.startswith("__")}


def error_of(src):
    """Return the BlazeError message raised by a snippet."""
    try:
        evaluate(src)
    except blaze.BlazeError as ex:
        return str(ex)
    raise AssertionError(f"expected a BlazeError from: {src}")


# ── README examples: the contract with users ─────────────────────

class TestReadmeExamples(unittest.TestCase):
    def test_euler_1(self):
        self.assertEqual(show("[1..100] | filter x -> x % 3 == 0 or x % 5 == 0 | sum"), "2418")

    def test_string_pipeline(self):
        self.assertEqual(
            show('"the quick brown fox" | words | map w -> upper(w) | join " "'),
            "THE QUICK BROWN FOX",
        )

    def test_sort_desc_take(self):
        self.assertEqual(show("[23, 45, 12, 67, 34, 89, 56, 78] | sort desc | take(3)"), "[89, 78, 67]")

    def test_fibonacci(self):
        src = "fib(n) -> if n <= 1 then n else fib(n-1) + fib(n-2)\n[fib(n) for n in 0..12]"
        self.assertEqual(show(src), "[0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]")

    def test_abs_expression(self):
        self.assertEqual(show("abs_val(x) -> if x < 0 then -x else x\nabs_val(-7)"), "7")

    def test_closures(self):
        src = (
            "make_adder(n) -> x -> x + n\n"
            "add5  = make_adder(5)\n"
            "add10 = make_adder(10)\n"
            "[add5(x) for x in 1..5]"
        )
        self.assertEqual(show(src), "[6, 7, 8, 9, 10]")
        self.assertEqual(show("make_adder(n) -> x -> x + n\nadd10 = make_adder(10)\n[add10(x) for x in 1..5]"),
                         "[11, 12, 13, 14, 15]")

    def test_statistics_block(self):
        data = "data = [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]\n"
        self.assertEqual(show(data + "data | mean"), "50.5")
        self.assertEqual(show(data + "data | std | round(2)"), "30.19")
        self.assertEqual(show(data + "data | median"), "50.5")
        self.assertEqual(show(data + "data | sort desc | take(3)"), "[90, 89, 78]")

    def test_corr_and_linreg(self):
        src = "corr([1, 2, 3, 4, 5], [2.1, 4.0, 5.9, 8.2, 10.1])"
        self.assertAlmostEqual(evaluate(src), 0.999412, places=6)
        reg = evaluate("linreg([1, 2, 3, 4, 5], [2.1, 4.0, 5.9, 8.2, 10.1])")
        self.assertAlmostEqual(reg["slope"], 2.02, places=6)
        self.assertAlmostEqual(reg["intercept"], 0.0, places=6)

    def test_range_literals(self):
        self.assertEqual(show("1..5"), "[1, 2, 3, 4, 5]")
        self.assertEqual(show("[1..5] | sum"), "15")
        self.assertEqual(show("[x*x for x in 1..10 if x % 2 == 0]"), "[4, 16, 36, 64, 100]")

    def test_string_interpolation(self):
        self.assertEqual(show('name = "Blaze"\nn = 42\n"Hello from {name}! The answer is {n * 2}."'),
                         "Hello from Blaze! The answer is 84.")

    def test_pattern_matching(self):
        src = (
            "grade(score) ->\n"
            "  match score\n"
            "  | >= 90 -> \"A\"\n"
            "  | >= 80 -> \"B\"\n"
            "  | >= 70 -> \"C\"\n"
            "  | >= 60 -> \"D\"\n"
            "  | _     -> \"F\"\n"
            "[grade(s) for s in [95, 83, 74, 55]]"
        )
        self.assertEqual(show(src), "[A, B, C, F]")

    def test_collections(self):
        self.assertEqual(show("[3, 1, 4, 1, 5, 9, 2, 6] | sort | unique"), "[1, 2, 3, 4, 5, 6, 9]")
        self.assertEqual(show('person = {name: "Alice", age: 30}\nperson.name'), "Alice")
        self.assertEqual(show('"blaze is fast blaze is fun" | words | frequency'),
                         "{blaze: 2, is: 2, fast: 1, fun: 1}")


# ── Core semantics ───────────────────────────────────────────────

class TestFunctions(unittest.TestCase):
    def test_return_inside_try_is_not_swallowed(self):
        src = "f() ->\n  try:\n    return 5\n  catch (e):\n    return 9\nf()"
        self.assertEqual(show(src), "5")

    def test_break_inside_try_is_not_swallowed(self):
        src = (
            "out = []\n"
            "for i in 1..5:\n"
            "  try:\n"
            "    if i == 3:\n"
            "      break\n"
            "    out = out + [i]\n"
            "  catch (e):\n"
            "    out = out + [-1]\n"
            "out"
        )
        self.assertEqual(show(src), "[1, 2]")

    def test_catch_still_catches_errors(self):
        src = "try:\n  nope()\ncatch (e):\n  \"caught\""
        self.assertEqual(show(src), "caught")

    def test_functions_do_not_leak_into_globals(self):
        src = "counter = 0\ninc() ->\n  counter = counter + 1\ninc()\ncounter"
        self.assertEqual(show(src), "0")

    def test_local_accumulation_inside_function(self):
        src = (
            "sum_to(n) ->\n"
            "  acc = 0\n"
            "  for i in 1..n:\n"
            "    acc = acc + i\n"
            "  return acc\n"
            "sum_to(5)"
        )
        self.assertEqual(show(src), "15")

    def test_parameters_shadow_globals(self):
        src = "x = 100\ndouble(x) -> x * 2\ndouble(3)"
        self.assertEqual(show(src), "6")
        self.assertEqual(show(src + "\nx"), "100")

    def test_default_parameters(self):
        src = "greet(name, greeting = \"Hello\") -> \"{greeting}, {name}!\"\ngreet(\"Blaze\")"
        self.assertEqual(show(src), "Hello, Blaze!")

    def test_recursion(self):
        src = "fact(n) -> if n <= 1 then 1 else n * fact(n-1)\nfact(10)"
        self.assertEqual(show(src), "3628800")

    def test_block_bodies_and_early_return(self):
        src = "sign(n) ->\n  if n > 0:\n    return 1\n  return -1\n[sign(3), sign(-3)]"
        self.assertEqual(show(src), "[1, -1]")

    def test_function_values_are_first_class(self):
        src = "apply(f, v) -> f(v)\napply(x -> x * 10, 4)"
        self.assertEqual(show(src), "40")


class TestBodyStatements(unittest.TestCase):
    """`print x` / `show x` are statements, and a `->` body is where a
    statement is often written, so both must work as a one-line body."""

    def test_lambda_body(self):
        self.assertEqual(output("map([1, 2], x -> print x)"), "1\n2\n")
        self.assertEqual(show("map([1, 2], x -> print x)"), "[null, null]")

    def test_function_body(self):
        self.assertEqual(output("f(x) -> print x\nf(7)"), "7\n")

    def test_parenthesised_lambda_body(self):
        self.assertEqual(output("f = (x) -> print x\nf(3)"), "3\n")

    def test_pipe_lambda_body(self):
        self.assertEqual(output("[1, 2] | map x -> print x"), "1\n2\n")

    def test_pipe_after_a_print_body_still_belongs_to_the_pipeline(self):
        src = "[1, 2] | map x -> print x | len"
        self.assertEqual(show(src), "2")
        self.assertEqual(output(src), "1\n2\n")

    def test_match_arm_body(self):
        src = (
            "g(n) ->\n"
            "  match n\n"
            "  | 1 -> print \"one\"\n"
            "  | _ -> print \"other\"\n"
            "g(1)"
        )
        self.assertEqual(output(src), "one\n")

    def test_show_body_returns_its_value(self):
        self.assertEqual(output("map([1, 2], x -> show x)"), "1\n2\n")
        self.assertEqual(show("map([1, 2], x -> show x)"), "[1, 2]")

    def test_bare_print_is_still_a_first_class_value(self):
        self.assertEqual(output("map([1, 2], print)"), "1\n2\n")
        self.assertEqual(show("apply(f) -> f\ntype(apply(print))"), "fn")


class TestIfBodyStatements(unittest.TestCase):
    """An inline `if ... then ... else ...` is the other place a one-line
    statement body gets written, so it must accept print/show too."""

    def test_then_and_else_bodies(self):
        src = "if {c} then print \"a\" else print \"b\""
        self.assertEqual(output(src.format(c="true")), "a\n")
        self.assertEqual(output(src.format(c="false")), "b\n")

    def test_else_body_only(self):
        self.assertEqual(output('x = if false then "a" else print "b"'), "b\n")

    def test_elif_body(self):
        src = 'if false then 1 elif true then print "e" else 2'
        self.assertEqual(output(src), "e\n")

    def test_show_bodies_return_their_value(self):
        self.assertEqual(show("if true then show 5 else show 6"), "5")
        self.assertEqual(show("if false then show 5 else show 6"), "6")

    def test_print_body_is_not_leaked_as_a_trailing_statement(self):
        # Before the fix the leftover "b" parsed as a second statement and
        # became the program's result.
        self.assertEqual(show('x = if false then "a" else print "b"'), "null")

    def test_inside_a_lambda_passed_to_a_call(self):
        src = "map([1, 2], x -> if x > 1 then print \"big\" else print \"small\")"
        self.assertEqual(output(src), "small\nbig\n")
        self.assertEqual(show(src), "[null, null]")

    def test_inside_a_function_body(self):
        src = 'f(c) -> if c then print "y" else print "n"\nf(false)'
        self.assertEqual(output(src), "n\n")

    def test_bare_print_before_else_is_still_a_value(self):
        self.assertEqual(show("type(if true then print else 1)"), "fn")
        self.assertEqual(output("if true then print else 1"), "")

    def test_ordinary_bodies_parse_as_before(self):
        self.assertEqual(show('if 1 > 2 then "yes" else "no"'), "no")
        self.assertEqual(show('if 1 > 2 then "yes" else "no" | len'), "2")


class TestCollections(unittest.TestCase):
    def test_group_by_keeps_native_keys(self):
        src = "g = group_by([1, 2, 3, 4], x -> x % 2)\ng[1]"
        self.assertEqual(show(src), "[1, 3]")

    def test_frequency_keeps_native_keys(self):
        self.assertEqual(show("frequency([1, 1, 2])"), "{1: 2, 2: 1}")

    def test_reduce(self):
        self.assertEqual(show("reduce([1, 2, 3], (a, b) -> a + b)"), "6")
        self.assertEqual(show("reduce([1, 2, 3], (a, b) -> a + b, 10)"), "16")
        self.assertEqual(show("reduce([7], (a, b) -> a * 100 + b, 3)"), "307")

    def test_reduce_empty_without_init_is_an_error(self):
        self.assertIn("empty list", error_of("reduce([], (a, b) -> a + b)"))

    def test_dict_and_list_comprehension(self):
        self.assertEqual(show("{x: x * x for x in 1..3}"), "{1: 1, 2: 4, 3: 9}")
        self.assertEqual(show("[x * 2 for x in 1..3 if x > 1]"), "[4, 6]")

    def test_indexing_and_fields(self):
        self.assertEqual(show("[10, 20, 30][1]"), "20")
        self.assertEqual(show("data = {a: [1, 2]}\ndata[\"a\"][0]"), "1")

    def test_while_and_break(self):
        src = "n = 0\nwhile true:\n  n = n + 1\n  if n == 3:\n    break\nn"
        self.assertEqual(show(src), "3")

    def test_list_concatenation(self):
        self.assertEqual(show("[1, 2] + [3]"), "[1, 2, 3]")

    def test_chunk_and_flatten(self):
        self.assertEqual(show("chunk(1..7, 3)"), "[[1, 2, 3], [4, 5, 6], [7]]")
        self.assertEqual(show("flat([[1, 2], [3]])"), "[1, 2, 3]")

    def test_pipe_with_bare_argument(self):
        self.assertEqual(show("[5, 3, 9] | take 2"), "[5, 3]")
        self.assertEqual(show('"a-b" | split "-"'), "[a, b]")


class TestStatistics(unittest.TestCase):
    DATA = "[23, 45, 12, 67, 34, 89, 56, 78, 11, 90]"

    def test_mean_median_std_var(self):
        d = [23, 45, 12, 67, 34, 89, 56, 78, 11, 90]
        self.assertAlmostEqual(evaluate(f"{self.DATA} | mean"), statistics.mean(d), places=9)
        self.assertAlmostEqual(evaluate(f"{self.DATA} | median"), statistics.median(d), places=9)
        self.assertAlmostEqual(evaluate(f"{self.DATA} | std"), statistics.stdev(d), places=9)
        self.assertAlmostEqual(evaluate(f"{self.DATA} | var"), statistics.variance(d), places=9)

    def test_percentile_agrees_with_median(self):
        self.assertAlmostEqual(evaluate("1..10 | percentile(50)"), 5.5, places=9)
        self.assertAlmostEqual(evaluate("1..10 | percentile(0)"), 1.0, places=9)
        self.assertAlmostEqual(evaluate("1..10 | percentile(100)"), 10.0, places=9)

    def test_percentile_rejects_bad_input(self):
        self.assertIn("0..100", error_of("[1, 2, 3] | percentile(150)"))
        self.assertIn("empty", error_of("[] | percentile(50)"))

    def test_normalize_and_zscore(self):
        self.assertEqual(show("[2, 4, 6] | normalize"), "[0.0, 0.5, 1.0]")
        z = evaluate("[1, 2, 3] | zscore")
        self.assertAlmostEqual(z[0], -1.0, places=9)
        self.assertAlmostEqual(z[2], 1.0, places=9)

    def test_describe(self):
        d = evaluate(f"{self.DATA} | describe")
        self.assertEqual(d["count"], 10)
        self.assertAlmostEqual(d["mean"], 50.5, places=6)
        self.assertAlmostEqual(d["median"], 50.5, places=6)

    def test_hist_prints_and_returns_input(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = evaluate("[1, 2, 2, 3] | hist")
        self.assertIn("Histogram", buf.getvalue())
        self.assertEqual(blaze.br(result), "[1, 2, 2, 3]")


class TestValueFormatting(unittest.TestCase):
    def test_floats_keep_precision(self):
        self.assertEqual(show("123456.789"), "123456.789")
        self.assertEqual(show("0.123456789"), "0.123456789")

    def test_whole_floats_keep_a_decimal_point(self):
        self.assertEqual(show("10.0"), "10.0")
        self.assertEqual(show("mean([1, 2])"), "1.5")

    def test_special_floats_are_printable(self):
        self.assertEqual(show("1/0"), "inf")
        self.assertEqual(show("-1/0"), "-inf")
        self.assertEqual(show("0/0"), "nan")

    def test_booleans_and_null(self):
        self.assertEqual(show("true"), "true")
        self.assertEqual(show("not false"), "true")
        self.assertEqual(show("null"), "null")

    def test_strings_print_without_quotes(self):
        self.assertEqual(output('print "sum: {1 + 1}"'), "sum: 2\n")


# ── Tables and files ─────────────────────────────────────────────

class TestTables(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = pathlib.Path(self.tmp.name) / "people.csv"
        rows = ["name,age,salary", "Alice,30,50000", "Bob,25,40000", "Cara,41,90000"]
        self.csv.write_text("\n".join(rows) + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_and_select(self):
        src = f't = load("{self.csv}")\nt | select_cols("name", "salary")'
        table = evaluate(src)
        self.assertEqual(table.cols, ["name", "salary"])
        self.assertEqual(table.nrows, 3)

    def test_where_filters_rows(self):
        src = f'load("{self.csv}") | where r -> r.age > 28'
        table = evaluate(src)
        self.assertEqual(table.data["name"], ["Alice", "Cara"])

    def test_where_is_linear(self):
        """where() must not rebuild every record for every row."""
        import time
        big = pathlib.Path(self.tmp.name) / "big.csv"
        big.write_text("a,b\n" + "".join(f"{i},{i * 2}\n" for i in range(2000)))
        src = f'load("{big}") | where r -> r.a > 1990 | len'
        start = time.perf_counter()
        self.assertEqual(evaluate(src), 9)
        self.assertLess(time.perf_counter() - start, 1.0, "where() looks quadratic")

    def test_table_ops(self):
        src = f't = load("{self.csv}")\n[t | len, len(t | head(2)), len(t | tail(1))]'
        self.assertEqual(show(src), "[3, 2, 1]")

    def test_describe_on_table(self):
        stats = evaluate(f'load("{self.csv}") | describe')
        self.assertEqual(stats["age"]["count"], 3)
        self.assertAlmostEqual(stats["age"]["mean"], 32.0, places=6)

    def test_json_round_trip(self):
        out = pathlib.Path(self.tmp.name) / "out.json"
        src = f'save_json([1, 2, 3], "{out}")\nload_json("{out}")'
        self.assertEqual(show(src), "[1, 2, 3]")


# ── Errors ───────────────────────────────────────────────────────

class TestErrors(unittest.TestCase):
    def test_undefined_variable(self):
        self.assertIn("Undefined: 'nope'", error_of("nope"))

    def test_index_error(self):
        self.assertIn("Index error", error_of("[1, 2, 3][10]"))

    def test_parse_error_reports_a_line(self):
        self.assertIn("Line 2", error_of("a = 1\nb = +"))

    def test_unknown_field_on_non_dict(self):
        self.assertIn("No field", error_of("x = 5\nx.name"))

    def test_cli_exit_codes(self):
        self.assertEqual(cli("-e", "1 + 1").returncode, 0)
        bad = cli("-e", "nope")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("Undefined", bad.stdout)


# ── CLI ──────────────────────────────────────────────────────────

class TestCli(unittest.TestCase):
    def test_eval_flag(self):
        self.assertEqual(cli("-e", "[1..4] | sum").stdout.strip(), "10")

    def test_version(self):
        self.assertIn("0.1", cli("--version").stdout)

    def test_file_mode_runs_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = pathlib.Path(tmp) / "s.blz"
            script.write_text('x = 2\nfor i in 1..3:\n  print "{x * i}"\n')
            res = cli(str(script))
            self.assertEqual(res.returncode, 0)
            self.assertEqual(res.stdout.split(), ["2", "4", "6"])

    def test_file_mode_does_not_echo_control_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = pathlib.Path(tmp) / "s.blz"
            script.write_text("if true:\n  1\nx = 5\n")
            self.assertEqual(cli(str(script)).stdout.strip(), "")

    def test_missing_file(self):
        res = cli("does-not-exist.blz")
        self.assertEqual(res.returncode, 1)
        self.assertIn("File not found", res.stdout)

    def test_repl_quits_cleanly(self):
        res = cli(stdin="1 + 1\nexit\n")
        self.assertEqual(res.returncode, 0)
        self.assertIn("→ 2", res.stdout)


# ── Documentation and examples must stay true ───────────────────

class TestDocsAndExamples(unittest.TestCase):
    def test_readme_builtin_table_only_lists_real_functions(self):
        text = (ROOT / "README.md").read_text()
        start = text.index("## Built-in Functions")
        section = text[start:text.index("## ", start + 5)]
        documented = set(re.findall(r"`([a-z_][a-z0-9_]*)`", section))
        self.assertTrue(documented, "README builtin table not found")
        missing = sorted(documented - stdlib())
        self.assertEqual(missing, [], f"README documents functions that do not exist: {missing}")

    def test_readme_claims_at_least_sixty_builtins(self):
        text = (ROOT / "README.md").read_text()
        count = int(re.search(r"Built-in Functions \((\d+)\+\)", text).group(1))
        callables = {k for k, v in blaze.Interpreter().genv.v.items()
                     if not k.startswith("__") and callable(v)}
        self.assertGreaterEqual(len(callables), count)

    def test_readme_states_the_real_builtin_count(self):
        text = (ROOT / "README.md").read_text()
        claimed = {int(n) for n in re.findall(r"(\d+) built-ins", text)}
        count = len({k for k, v in blaze.Interpreter().genv.v.items()
                    if not k.startswith("__") and callable(v)})
        self.assertEqual(claimed, {count}, f"README claims {claimed} built-ins, interpreter has {count}")

    def test_readme_example_files_exist(self):
        text = (ROOT / "README.md").read_text()
        for name in re.findall(r"\[`([a-z_]+\.blz)`\]\(examples/", text):
            self.assertTrue((ROOT / "examples" / name).is_file(), f"README links to missing examples/{name}")

    def test_every_example_script_runs(self):
        examples = sorted((ROOT / "examples").glob("*.blz"))
        self.assertGreaterEqual(len(examples), 5, "examples/ directory is missing")
        for path in examples:
            with self.subTest(example=path.name):
                res = cli(str(path))
                self.assertEqual(res.returncode, 0, f"{path.name} failed:\n{res.stdout}{res.stderr}")
                self.assertTrue(res.stdout.strip(), f"{path.name} produced no output")

    def test_help_lists_only_working_syntax(self):
        out = cli("--help").stdout
        self.assertIn("PIPES", out)
        self.assertNotIn("fn stats", out, "HELP advertises an unimplemented 'fn' keyword")


if __name__ == "__main__":
    unittest.main(verbosity=2)
