# pytest in an Afternoon: A Hands-On Tutorial (with Robot Framework)

Nov 13, 2026 · @Shubham

## How to use this tutorial

You learn pytest here by testing one small package, `ecusim`, a simulated ECU that accepts OTA firmware updates. Type the code yourself, run every command, and do the exercise at the end of each module. Every example was run against pytest 9.1.1 and 9.2.0, pytest-robotframework 4.6.3, Robot Framework 7.5.1 and uv 0.11.32 on Python 3.13 before it went into this doc.

The full course takes about 5 hours. Skip the tasks marked *Stretch* to finish in about 3.5 hours.

| Module | Topic | Minutes |
| --- | --- | --- |
| Setup | Project and environment | 15 |
| 0 | uv, the lockfile and your test environment | 30 |
| 1 | First tests, discovery, the command line | 20 |
| 2 | Assertions and exceptions | 20 |
| 3 | Fixtures | 45 |
| 4 | Parametrization | 25 |
| 5 | Markers, skip and xfail | 25 |
| 6 | Built-in fixtures and mocking | 30 |
| 7 | Configuration, plugins and hooks | 25 |
| 8 | Robot Framework with pytest-robotframework | 40 |
| 9 | Capstone | 30 |

### Setup (15 min)

pytest 9 needs Python 3.10 or newer. Create this layout:

```text
ecusim-tutorial/
├── pyproject.toml
├── src/ecusim/__init__.py      (empty)
├── src/ecusim/version.py
├── src/ecusim/ecu.py
├── tests/                      (modules 1-7)
└── robot_tests/                (module 8)
```

`pyproject.toml`:

```toml
[project]
name = "ecusim"
version = "0.1.0"
requires-python = ">=3.10"

[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

`src/ecusim/version.py`:

```python
"""Firmware version parsing and comparison."""


def parse_version(text: str) -> tuple[int, int, int]:
    """Turn '1.4.2' into (1, 4, 2). Raises ValueError on bad input."""
    parts = text.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"expected MAJOR.MINOR.PATCH, got {text!r}")
    try:
        major, minor, patch = (int(p) for p in parts)
    except ValueError:
        raise ValueError(f"non-numeric version part in {text!r}") from None
    if min(major, minor, patch) < 0:
        raise ValueError(f"negative version part in {text!r}")
    return major, minor, patch


def is_newer(candidate: str, installed: str) -> bool:
    return parse_version(candidate) > parse_version(installed)
```

`src/ecusim/ecu.py`:

```python
"""A tiny simulated ECU that can receive OTA updates."""

import json
import logging
import os
import time
from pathlib import Path

from ecusim.version import is_newer

log = logging.getLogger("ecusim")


class EcuError(Exception):
    pass


class Ecu:
    def __init__(self, name: str, firmware: str = "1.0.0") -> None:
        self.name = name
        self.firmware = firmware
        self.connected = False
        self.battery_voltage = 12.6

    def connect(self) -> None:
        log.info("connecting to %s", self.name)
        self.connected = True

    def disconnect(self) -> None:
        log.info("disconnecting from %s", self.name)
        self.connected = False

    def read_voltage(self) -> float:
        self._require_connection()
        return self.battery_voltage

    def install(self, version: str) -> None:
        """Install an OTA update. Only upgrades are allowed."""
        self._require_connection()
        if self.battery_voltage < 11.5:
            raise EcuError("battery too low for update")
        if not is_newer(version, self.firmware):
            log.warning("rejected %s: not newer than %s", version, self.firmware)
            raise EcuError(f"{version} is not newer than {self.firmware}")
        time.sleep(flash_delay())
        self.firmware = version
        log.info("%s now runs %s", self.name, version)

    def _require_connection(self) -> None:
        if not self.connected:
            raise EcuError(f"{self.name} is not connected")


def flash_delay() -> float:
    """Seconds a flash takes. Override with ECUSIM_FLASH_DELAY."""
    return float(os.environ.get("ECUSIM_FLASH_DELAY", "2"))


def load_fleet(path: Path) -> list[Ecu]:
    """Read a JSON file like [{"name": "HU", "firmware": "1.2.0"}]."""
    data = json.loads(Path(path).read_text())
    return [Ecu(item["name"], item.get("firmware", "1.0.0")) for item in data]


def report(ecus: list[Ecu]) -> None:
    for ecu in ecus:
        print(f"{ecu.name}: {ecu.firmware}")
```

Note the 2-second flash delay. It is there on purpose: you will learn three ways to make tests not wait for it.

Do not install anything yet. Module 0 creates the environment with uv. If you cannot use uv, the pip equivalent is a virtual environment, `pip install -e .`, then `pip install pytest pytest-cov pytest-xdist pytest-mock`.

## Module 0: uv, the lockfile and your test environment (30 min)

uv replaces `pip`, `venv` and `pip-tools` with one tool, and in a project its job is to keep three things in agreement: what you asked for, what was resolved, and what is installed. You set up the tutorial environment with it here and use it to run every test afterwards.

| File | Holds | Who writes it | In git? |
| --- | --- | --- | --- |
| `pyproject.toml` | Your requirements, as broad ranges such as `pytest>=9.2.0` | You, or `uv add` / `uv remove` | Yes |
| `uv.lock` | The exact version, source and hashes of every package, direct and transitive | uv only | Yes |
| `.venv/` | The installed packages | uv only | No |

**Locking** is resolving `pyproject.toml` into `uv.lock`. **Syncing** is installing from `uv.lock` into `.venv`. Almost everything else in uv is a variation on those two steps ([locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)).

### Create the environment

Install uv once per machine. `pip install uv` works; the uv docs also list standalone installers. Then, in the project root:

```bash
uv add --dev pytest pytest-cov pytest-xdist pytest-mock
```

That one command did four things:

1. Created `.venv/` with a Python that satisfies `requires-python`.
2. Wrote a `[dependency-groups]` table into `pyproject.toml`, each entry with a lower bound at the latest version.
3. Resolved everything and wrote `uv.lock`.
4. Installed the packages, plus `ecusim` itself in editable mode, so `import ecusim` works in tests and your edits take effect without reinstalling.

```toml
[dependency-groups]
dev = [
    "pytest>=9.2.0",
    "pytest-cov>=7.1.0",
    "pytest-mock>=3.17.0",
    "pytest-xdist>=3.8.0",
]
```

Dependency groups are for tools you need while developing. They are never published with the package, unlike `[project.dependencies]`. The `dev` group is special: uv installs it by default.

### Run things with uv run

```bash
uv run pytest --version
uv run python -c "import ecusim; print(ecusim.__file__)"
```

`uv run` first checks that the lockfile matches `pyproject.toml` and that `.venv` matches the lockfile, repairs either if needed, then runs the command inside the environment. You never activate anything and never run a stale environment.

From here on, run every `pytest ...` command in this tutorial as `uv run pytest ...`. If you prefer to type plain `pytest`, activate the environment once per shell with `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate`.

### Read the lockfile

Open `uv.lock`. It is TOML with one `[[package]]` entry per package. Trimmed, from my run:

```toml
version = 1
requires-python = ">=3.10"
resolution-markers = [
    "python_full_version >= '3.11'",
    "python_full_version < '3.11'",
]

[[package]]
name = "coverage"
version = "7.16.2"
source = { registry = "https://pypi.org/simple" }
resolution-markers = [
    "python_full_version < '3.11'",
]
sdist = { url = "https://files.pythonhosted.org/...", hash = "sha256:ca64d9..." }
wheels = [
    { url = "https://.../coverage-7.16.2-cp310-cp310-win_amd64.whl", hash = "sha256:c3305c..." },
]

[[package]]
name = "ecusim"
version = "0.1.0"
source = { editable = "." }

[package.dev-dependencies]
dev = [
    { name = "pytest" },
    { name = "pytest-cov" },
]
```

Four things to notice:

- **It is universal.** One file covers every operating system, CPU architecture and Python version your project allows. That is why the Windows wheel is listed even though I locked on Linux, and why a colleague on another platform gets the same versions.
- **It can fork.** In my lockfile `coverage` appears twice: 7.16.2 for Python 3.10 and a newer release for 3.11 and up, because the newer one dropped 3.10. `resolution-markers` records which entry applies where. Your versions may differ.
- **Hashes pin the artifact, not only the version.** A re-uploaded or tampered file fails the install.
- **Your own project is in it**, as an editable source, with its groups.

Commit `uv.lock`. Never edit it by hand; change `pyproject.toml` and let uv re-lock. The format is specific to uv ([project layout](https://docs.astral.sh/uv/concepts/projects/layout/)).

### The commands

| Command | Lock step | Sync step |
| --- | --- | --- |
| `uv lock` | Updates `uv.lock` if needed | None |
| `uv lock --check` | Only checks; exit code 1 if outdated | None |
| `uv sync` | Updates if needed | Makes `.venv` match exactly, removing extras |
| `uv run <cmd>` | Updates if needed | Installs what is missing, removes nothing |
| `uv add <pkg>` / `uv remove <pkg>` | Edits `pyproject.toml`, then updates | Syncs |
| `uv tree` | Updates if needed | None; prints the dependency tree |

Run `uv tree` now to see which package pulled in which.

The difference between `uv sync` (exact) and `uv run` (inexact) matters in module 8: a plugin installed for one run stays in `.venv` until the next `uv sync`.

### When is the lockfile outdated?

uv compares the lockfile with `pyproject.toml` only. Adding a dependency, or changing a range so that it excludes the locked version, makes it outdated. A new release on PyPI does not. That is the point of a lockfile: the same commit installs the same packages next month.

So upgrades are always deliberate:

| Command | Effect |
| --- | --- |
| `uv lock --upgrade` | Move every package to the newest version your ranges allow |
| `uv lock --upgrade-package pytest` | Move only pytest; everything else stays locked |
| `uv lock --upgrade-package pytest --dry-run` | Show what would change without writing |

Review the diff of `uv.lock` in the commit, then run the tests. A test suite plus a lockfile is what makes dependency upgrades safe.

### Three flags for CI

| Flag | Behaviour | Use |
| --- | --- | --- |
| `--locked` | Error if `uv.lock` is outdated, instead of updating it | CI installs: `uv sync --locked` |
| `--frozen` | Use `uv.lock` as it is, without checking it | When you trust the lockfile and want no check, even if it disagrees with `pyproject.toml` |
| `--no-sync` | Do not touch `.venv` before running | A step after an explicit sync |

A CI job for this project is therefore two lines:

```bash
uv sync --locked
uv run --no-sync pytest --junitxml=report.xml
```

If someone edited `pyproject.toml` and forgot to commit the new lockfile, the first line fails with `The lockfile at uv.lock needs to be updated, but --locked was provided`.

### Groups, extras and export

- More groups: `uv add --group robot <pkg>` creates a `robot` group. Only `dev` is installed by default; select others with `uv sync --group robot` or `uv run --group robot ...`. `--no-dev` leaves `dev` out and `--all-groups` takes everything.
- All groups are resolved together into one lockfile, so they can never disagree on a version.
- Extras (`[project.optional-dependencies]`) are different: they are published with your package for its users. Test tools belong in groups.
- For tools that cannot read `uv.lock`: `uv export --format requirements.txt` or `uv export --format pylock.toml`.
- A one-off package without touching the project: `uv run --with rich python script.py`.
- A new project from nothing: `uv init --package name` writes the `pyproject.toml`, a `src/` layout and a `.gitignore` for you.

Group flags and defaults are in the [dependencies page](https://docs.astral.sh/uv/concepts/projects/dependencies/).

### Exercise 0

1. Run `uv lock --check` and confirm exit code 0.
2. Add `dependencies = ["packaging>=24"]` under `[project]` by hand. Run `uv lock --check`, then `uv sync --locked`, and read both errors. Run `uv lock` and look at the diff of `uv.lock`. Then remove the line and lock again.
3. Delete `.venv/` and run `uv sync`. Note how long a full rebuild from the lockfile takes.
4. Run `uv lock --upgrade --dry-run` and read what it would change.
5. *Stretch:* run `uv export --format requirements.txt --no-hashes` and compare its pins with `uv tree`.

## Module 1: First tests and the command line (20 min)

A pytest test is a plain function whose name starts with `test_` and that uses a bare `assert`. There is no base class and no `self.assertEqual`.

Create `tests/test_version.py`:

```python
from ecusim.version import is_newer, parse_version


def test_parse_simple_version():
    assert parse_version("1.4.2") == (1, 4, 2)


def test_parse_strips_whitespace():
    assert parse_version(" 2.0.1\n") == (2, 0, 1)


def test_newer_version_is_detected():
    assert is_newer("1.10.0", "1.9.9")


def test_deliberate_failure():
    assert parse_version("1.4.2") == (1, 4, 3)
```

Run `pytest` from the project root. You get three dots and one `F`, then a failure report:

```text
    def test_deliberate_failure():
>       assert parse_version("1.4.2") == (1, 4, 3)
E       assert (1, 4, 2) == (1, 4, 3)
E
E         At index 2 diff: 2 != 3
```

pytest rewrites `assert` statements at import time, so it can show the values on both sides and where they differ. That is why a bare `assert` is all you need.

### How pytest finds tests

With default settings pytest collects:

- files named `test_*.py` or `*_test.py`, searched recursively from the current directory or from `testpaths`
- functions named `test*` at module level
- methods named `test*` inside classes named `Test*` that have no `__init__`

Classes are optional. Use them only to group related tests; a fresh instance is created for every test method, so they do not share state through `self`.

Every test has a node ID such as `tests/test_version.py::test_parse_simple_version`. You can pass a node ID to run exactly that test.

### Commands you will use every day

| Command | Effect |
| --- | --- |
| `pytest` | Run everything |
| `pytest tests/test_version.py` | Run one file |
| `pytest tests/test_version.py::test_parse_simple_version` | Run one test by node ID |
| `pytest -k "parse and not whitespace"` | Select by name expression |
| `pytest -v` / `-q` | More / less output per test |
| `pytest -x` | Stop at the first failure |
| `pytest --lf` | Re-run only the tests that failed last time |
| `pytest --ff` | Run last failures first, then the rest |
| `pytest -s` | Do not capture output, so `print` shows live |
| `pytest -l` | Show local variables in tracebacks |
| `pytest --pdb` | Drop into the debugger on failure |
| `pytest --collect-only -q` | List tests without running them |
| `pytest -ra` | Summary of everything that did not pass |
| `pytest --durations=5` | Show the five slowest tests |

The exit code is 0 when all tests pass, 1 when tests fail, and 5 when no tests were collected. CI relies on this.

### Exercise 1

1. Run only the deliberate failure with `-k`, then with its node ID.
2. Run `pytest --lf` and check that only one test runs.
3. Run `pytest --collect-only -q` and read the node IDs.
4. *Stretch:* wrap the two parse tests in a `class TestParse:` and select them with `pytest -k TestParse`.

Leave the deliberate failure in the file. You will use it again in module 2.

## Module 2: Assertions and exceptions (20 min)

Three tools cover almost every check: bare `assert` for values, `pytest.raises` for expected exceptions, and `pytest.approx` for floats.

Add `import pytest` at the top of `tests/test_version.py` and append:

```python
def test_rejects_two_part_version():
    with pytest.raises(ValueError):
        parse_version("1.4")


def test_error_message_names_the_input():
    with pytest.raises(ValueError, match=r"non-numeric .* '1\.x\.0'"):
        parse_version("1.x.0")


def test_inspect_the_exception():
    with pytest.raises(ValueError) as excinfo:
        parse_version("1.-4.2")
    assert "negative" in str(excinfo.value)


def test_voltage_is_close_enough():
    assert 0.1 + 0.2 == pytest.approx(0.3)
    assert 12.58 == pytest.approx(12.6, abs=0.05)


def test_dict_diff():
    actual = {"name": "HU", "fw": "1.0.0", "ok": True}
    assert actual == {"name": "HU", "fw": "1.0.1", "ok": True}
```

What each one does:

- `pytest.raises(Exc)` passes only if the block raises `Exc` or a subclass. If nothing is raised, the test fails.
- `match=` runs `re.search` against the exception message. It is a regex, so escape dots and brackets.
- `as excinfo` gives you the exception afterwards as `excinfo.value`, plus `excinfo.type` and `excinfo.traceback`.
- `pytest.approx` compares with a relative tolerance of 1e-6 by default. Pass `rel=` or `abs=` to change it. It also works on lists, dicts and numpy arrays.

Keep only the one call that should raise inside the `with` block. Any line after it in the block never runs.

Run `pytest tests/test_version.py`. `test_dict_diff` fails with a targeted diff:

```text
E         Omitting 2 identical items, use -vv to show
E         Differing items:
E         {'fw': '1.0.0'} != {'fw': '1.0.1'}
```

pytest produces diffs like this for strings, sequences, sets, dicts and dataclasses. Use `-vv` for the full, untruncated comparison.

You can add a message after a comma, as in `assert ecu.connected, "ECU dropped the connection"`. It appears in the failure report alongside the introspected values.

### Exercise 2

1. Write a test proving that `parse_version("")` raises `ValueError` with a message containing `MAJOR.MINOR.PATCH`.
2. Change `test_voltage_is_close_enough` so the second assert fails, and read how `approx` reports the tolerance.
3. Delete `test_deliberate_failure` and `test_dict_diff`. The suite should be green from here on.
4. *Stretch:* read about `pytest.warns` and `pytest.RaisesGroup` in the [assertion how-to](https://docs.pytest.org/en/stable/how-to/assert.html).

## Module 3: Fixtures (45 min)

A fixture is a function that prepares something a test needs; a test asks for it by naming it as a parameter. Fixtures replace `setUp`/`tearDown` and are the most important pytest concept, so this is the longest module.

### A fixture with teardown

Create `tests/conftest.py`:

```python
import pytest

from ecusim.ecu import Ecu


@pytest.fixture
def ecu():
    """A connected head unit, disconnected again after the test."""
    unit = Ecu("HU", firmware="1.0.0")
    unit.connect()
    yield unit
    unit.disconnect()
```

Create `tests/test_ecu.py`:

```python
import pytest

from ecusim.ecu import Ecu, EcuError


def test_fresh_ecu_is_disconnected():
    assert not Ecu("HU").connected


def test_install_upgrades_firmware(ecu):
    ecu.install("1.1.0")
    assert ecu.firmware == "1.1.0"


def test_downgrade_is_rejected(ecu):
    with pytest.raises(EcuError, match="not newer"):
        ecu.install("0.9.0")
    assert ecu.firmware == "1.0.0"


def test_reading_voltage_needs_connection():
    with pytest.raises(EcuError, match="not connected"):
        Ecu("HU").read_voltage()
```

How it works:

- pytest sees the parameter `ecu`, finds the fixture with that name, runs it up to `yield`, and passes the yielded value into the test.
- Code after `yield` is teardown. It runs even when the test fails.
- Each test gets its own fresh `Ecu`, so tests cannot affect each other.
- `conftest.py` is a special file. Fixtures in it are available to every test in that directory and below, with no import.

Run `pytest tests/test_ecu.py --durations=3`. One test takes 2 seconds because `install` really sleeps. Fix that next.

### autouse fixtures

Add to `conftest.py`:

```python
@pytest.fixture(autouse=True)
def fast_flash(monkeypatch):
    """Every test flashes instantly instead of waiting 2 seconds."""
    monkeypatch.setenv("ECUSIM_FLASH_DELAY", "0")
```

`autouse=True` applies the fixture to every test in scope without the test asking for it. Note that a fixture can request other fixtures: here it uses the built-in `monkeypatch`, which undoes the environment change after each test. Run again and the suite is instant.

Use autouse sparingly. It is invisible at the test, which makes failures harder to trace.

### Factory fixtures

When a test needs several objects, or needs to choose arguments, return a function instead of a value. Add to `conftest.py`:

```python
@pytest.fixture
def make_ecu():
    """Factory fixture: build as many ECUs as a test needs."""
    created = []

    def _make(name="HU", firmware="1.0.0", voltage=12.6):
        unit = Ecu(name, firmware)
        unit.battery_voltage = voltage
        unit.connect()
        created.append(unit)
        return unit

    yield _make
    for unit in created:
        unit.disconnect()
```

Add to `test_ecu.py`:

```python
def test_low_battery_blocks_update(make_ecu):
    weak = make_ecu(voltage=11.0)
    with pytest.raises(EcuError, match="battery too low"):
        weak.install("2.0.0")


def test_two_ecus_update_independently(make_ecu):
    hu = make_ecu("HU")
    tcu = make_ecu("TCU", firmware="3.0.0")
    hu.install("1.5.0")
    assert (hu.firmware, tcu.firmware) == ("1.5.0", "3.0.0")
```

### Scope

By default a fixture runs once per test. For expensive resources, such as a test bench, a database or a flashed ECU, widen the scope. Add to `conftest.py`:

```python
@pytest.fixture(scope="session")
def bench():
    """Pretend this is an expensive test bench that boots once per run."""
    print("\n[bench] power on")
    yield {"supply": "PSU-1", "booted": True}
    print("\n[bench] power off")
```

Add to `test_ecu.py`:

```python
def test_bench_is_booted(bench, ecu):
    assert bench["booted"]
    assert ecu.connected


def test_bench_is_shared(bench):
    assert bench["supply"] == "PSU-1"
```

Run `pytest tests/test_ecu.py -k bench --setup-show`:

```text
SETUP    S bench
        SETUP    F monkeypatch
        SETUP    F fast_flash (fixtures used: monkeypatch)
        SETUP    F ecu
        tests/test_ecu.py::test_bench_is_booted (fixtures used: bench, ecu, fast_flash, monkeypatch).
        TEARDOWN F ecu
        TEARDOWN F fast_flash
        TEARDOWN F monkeypatch
        ...
TEARDOWN S bench
```

`S` is session scope and `F` is function scope. The bench is set up once and torn down last; teardown always runs in reverse order of setup.

| Scope | Runs once per | Typical use |
| --- | --- | --- |
| `function` (default) | test | Anything cheap or mutable |
| `class` | test class | Shared state for a group of methods |
| `module` | test file | A resource one file's tests share |
| `package` | directory | Rarely needed |
| `session` | whole run | Benches, servers, expensive connections |

Two rules follow from scope. A wider fixture cannot request a narrower one: a session fixture cannot use `monkeypatch` or `tmp_path`, because those are function-scoped. And anything in a wide fixture is shared, so tests must not mutate it.

### Exercise 3

1. Run `pytest --fixtures tests` and find your four fixtures and their docstrings in the output.
2. Make `ecu` fail in teardown by adding `assert False` after the `yield`. Run the suite and see how pytest reports an `ERROR` separately from a test failure. Remove it again.
3. Write a fixture `updated_ecu` that requests `ecu`, installs `1.1.0` and returns it. Write a test that uses it to check a second update to `1.2.0`.
4. *Stretch:* change `ecu` to `scope="module"`, run the file, and work out which test now fails and why. Change it back.

## Module 4: Parametrization (25 min)

`@pytest.mark.parametrize` runs one test function once per row of data, and reports each row as its own test. Use it whenever you would otherwise copy a test and change the values.

Create `tests/test_parametrize.py`:

```python
import pytest

from ecusim.ecu import Ecu
from ecusim.version import is_newer, parse_version


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.4.2", (1, 4, 2)),
        ("0.0.1", (0, 0, 1)),
        ("10.20.30", (10, 20, 30)),
    ],
)
def test_parse_version(text, expected):
    assert parse_version(text) == expected


@pytest.mark.parametrize("bad", ["", "1.4", "1.4.2.0", "a.b.c", "1.-1.0"])
def test_parse_rejects(bad):
    with pytest.raises(ValueError):
        parse_version(bad)
```

Run `pytest tests/test_parametrize.py -v`. Each case has its own node ID, for example `test_parse_rejects[1.4]`, and passes or fails on its own. Quote the node ID in the shell when you run a single case: `pytest "tests/test_parametrize.py::test_parse_rejects[1.4]"`.

### Readable IDs and per-case marks

Auto-generated IDs like `1.4.2-expected0` are hard to read. `pytest.param` lets you name a case and attach marks to it:

```python
@pytest.mark.parametrize(
    ("candidate", "installed", "newer"),
    [
        pytest.param("1.0.1", "1.0.0", True, id="patch-bump"),
        pytest.param("1.10.0", "1.9.0", True, id="numeric-not-lexical"),
        pytest.param("1.0.0", "1.0.0", False, id="same-version"),
        pytest.param("2.0.0", "10.0.0", False, id="older-major"),
        pytest.param(
            "1.0.0-rc1", "0.9.0", True, id="prerelease",
            marks=pytest.mark.xfail(reason="pre-release tags not supported yet", raises=ValueError),
        ),
    ],
)
def test_is_newer(candidate, installed, newer):
    assert is_newer(candidate, installed) is newer
```

The last case is a known gap, marked as an expected failure. Module 5 explains `xfail`.

### Stacking gives the cross product

```python
@pytest.mark.parametrize("name", ["HU", "TCU"])
@pytest.mark.parametrize("target", ["1.1.0", "2.0.0"])
def test_every_ecu_takes_every_update(name, target):
    unit = Ecu(name)
    unit.connect()
    unit.install(target)
    assert unit.firmware == target
```

Two decorators with two values each produce four tests.

### Parametrized fixtures

Put `params` on a fixture and every test that uses it runs once per value. This suits "run the whole suite against each ECU variant" better than decorating every test.

```python
@pytest.fixture(params=["HU", "TCU", "RSE"])
def any_ecu(request):
    unit = Ecu(request.param)
    unit.connect()
    yield unit
    unit.disconnect()


def test_all_ecus_report_voltage(any_ecu):
    assert any_ecu.read_voltage() == pytest.approx(12.6)
```

`request` is a built-in fixture that describes the requesting test. `request.param` holds the current value.

### Subtests

Parametrize needs its data at collection time, before any test runs. When the data only exists at run time, for example a list of ECUs read from the bench, use the `subtests` fixture, new in pytest 9.0:

```python
def test_fleet_versions(subtests):
    fleet = {"HU": "1.2.0", "TCU": "3.0.1", "RSE": "0.9.4"}
    for name, firmware in fleet.items():
        with subtests.test(ecu=name):
            assert parse_version(firmware) >= (0, 9, 0)
```

A failing subtest is reported as `SUBFAILED` and the loop continues. The trade-off: subtests have no node ID, so you cannot select or re-run one alone. The pytest docs still label the feature experimental. Prefer parametrize when the data is known up front.

### Exercise 4

1. Add the case `("1.2.3", "1.2.10", False)` to `test_is_newer` with a meaningful `id`.
2. Run only the `patch-bump` case with `-k`.
3. Write one parametrized test for `Ecu.install` with rows of `(voltage, should_succeed)` for 11.0, 11.5 and 12.6 volts. Use `make_ecu`. Hint: branch on `should_succeed` and use `pytest.raises` in one branch.
4. *Stretch:* rewrite task 3 without the branch by parametrizing an `expectation` argument with `pytest.raises(EcuError)` and `contextlib.nullcontext()`.

## Module 5: Markers, skip and xfail (25 min)

A marker is a label on a test. Built-in markers change how a test runs (`skip`, `skipif`, `xfail`, `parametrize`); your own markers let you select groups of tests with `-m`.

Create `tests/test_markers.py`:

```python
import sys
import time

import pytest

from ecusim.ecu import EcuError
from ecusim.version import parse_version


@pytest.mark.slow
def test_real_flash_takes_time(ecu, monkeypatch):
    monkeypatch.setenv("ECUSIM_FLASH_DELAY", "0.3")
    start = time.perf_counter()
    ecu.install("1.1.0")
    assert time.perf_counter() - start >= 0.3


@pytest.mark.hil
def test_on_real_bench(bench):
    assert bench["booted"]


@pytest.mark.skip(reason="rollback not implemented yet")
def test_rollback(ecu):
    ecu.rollback()


@pytest.mark.skipif(sys.platform != "win32", reason="CANoe only runs on Windows")
def test_canoe_bridge():
    import win32com.client  # noqa: F401


@pytest.mark.xfail(reason="bug #42: leading 'v' not stripped", raises=ValueError, strict=True)
def test_version_with_v_prefix():
    assert parse_version("v1.2.3") == (1, 2, 3)


def test_skip_at_runtime(ecu):
    if ecu.read_voltage() > 12.0:
        pytest.skip("only meaningful on a weak battery")
    with pytest.raises(EcuError):
        ecu.install("9.9.9")


def test_optional_dependency():
    np = pytest.importorskip("numpy_does_not_exist")
    assert np
```

### Register your markers

`slow` and `hil` are custom markers. Unregistered markers only produce a warning, so a typo like `@pytest.mark.solw` silently creates a new marker. Register them and make unknown ones an error. Add to `pyproject.toml`:

```toml
[tool.pytest]
addopts = ["-ra", "--strict-markers"]
markers = [
    "slow: takes more than a moment; deselect with -m 'not slow'",
    "hil: needs the real test bench",
]
```

`[tool.pytest]` with real TOML lists needs pytest 9.0 or newer. On older versions the table is `[tool.pytest.ini_options]` and `addopts` is a single string.

Run `pytest tests/test_markers.py`. With `-ra` in `addopts`, the summary lists every skip and xfail with its reason.

### What each marker means

| Marker or call | Use it when | Result |
| --- | --- | --- |
| `@pytest.mark.skip(reason=...)` | The test cannot run at all right now | `SKIPPED`, body never runs |
| `@pytest.mark.skipif(cond, reason=...)` | It cannot run on this platform or version | `SKIPPED` if `cond` is true |
| `pytest.skip("...")` | You only know at run time | `SKIPPED` from that line on |
| `pytest.importorskip("mod")` | An optional dependency is missing | `SKIPPED` if the import fails |
| `@pytest.mark.xfail(reason=...)` | A known bug: the test should pass one day | `XFAIL` if it fails, `XPASS` if it passes |

Skip means "not applicable here". Xfail means "this is broken and we know it". The test body of an xfail test does run.

Two `xfail` arguments are worth using every time. `raises=ValueError` makes the test count as xfailed only for that exception, so a different error still shows up as a real failure. `strict=True` turns an unexpected pass into a failure, so you notice when the bug is fixed and remove the marker.

### Selecting by marker

| Command | Runs |
| --- | --- |
| `pytest -m slow` | Only tests marked `slow` |
| `pytest -m "not slow"` | Everything except `slow` |
| `pytest -m "not slow and not hil"` | The quick local suite |
| `pytest --markers` | Nothing; lists all registered markers |

`-m` matches markers and `-k` matches names. Both accept `and`, `or`, `not` and parentheses.

To mark every test in a file, set `pytestmark = pytest.mark.slow` at module level. A marker on a class applies to all its methods.

### Exercise 5

1. Fix bug #42: make `parse_version` strip one leading `v`. Run the suite and see the strict xfail turn into a failure. Then remove the marker.
2. Run the suite without the slow tests and confirm one test is deselected.
3. Misspell a marker and check that `--strict-markers` stops the run at collection.
4. *Stretch:* add a third marker `ota`, register it, and apply it to all of `test_ecu.py` with `pytestmark`.

## Module 6: Built-in fixtures and mocking (30 min)

pytest ships fixtures for the four things tests most often need to control: files, the environment, printed output and logs. All of them clean up after themselves.

Create `tests/test_builtin_fixtures.py`:

```python
import json
import logging

import pytest

from ecusim import ecu as ecu_module
from ecusim.ecu import Ecu, EcuError, flash_delay, load_fleet, report
```

### tmp\_path: files

```python
def test_load_fleet_from_file(tmp_path):
    fleet_file = tmp_path / "fleet.json"
    fleet_file.write_text(json.dumps([{"name": "HU", "firmware": "1.2.0"}, {"name": "TCU"}]))

    fleet = load_fleet(fleet_file)

    assert [(e.name, e.firmware) for e in fleet] == [("HU", "1.2.0"), ("TCU", "1.0.0")]
```

`tmp_path` is a `pathlib.Path` to a new empty directory, unique per test. pytest keeps the directories of the last three runs for debugging and deletes older ones. For a session-scoped fixture, use `tmp_path_factory` instead.

### monkeypatch: environment and attributes

```python
def test_flash_delay_default(monkeypatch):
    monkeypatch.delenv("ECUSIM_FLASH_DELAY", raising=False)
    assert flash_delay() == 2.0


def test_flash_delay_from_env(monkeypatch):
    monkeypatch.setenv("ECUSIM_FLASH_DELAY", "0.5")
    assert flash_delay() == 0.5


def test_install_sleeps_for_flash_delay(ecu, monkeypatch):
    naps = []
    monkeypatch.setattr(ecu_module, "flash_delay", lambda: 7.0)
    monkeypatch.setattr(ecu_module.time, "sleep", naps.append)

    ecu.install("1.1.0")

    assert naps == [7.0]
```

`monkeypatch` changes something for one test and restores it afterwards. Its main methods are `setenv`, `delenv`, `setattr`, `delattr`, `setitem`, `chdir` and `syspath_prepend`.

The third test replaces `time.sleep` with `naps.append`, so the test records the requested delay instead of waiting 7 seconds.

Patch a name where it is looked up, not where it is defined. `install` calls `flash_delay` through the `ecusim.ecu` module, so that is the module to patch. If another module did `from ecusim.ecu import flash_delay`, you would patch the name in that other module.

### capsys: printed output

```python
def test_report_prints_one_line_per_ecu(capsys):
    report([Ecu("HU", "1.2.0"), Ecu("TCU", "3.0.0")])

    out = capsys.readouterr().out

    assert out == "HU: 1.2.0\nTCU: 3.0.0\n"
```

pytest captures stdout and stderr by default and shows them only for failing tests. `capsys.readouterr()` returns what was captured so far as `.out` and `.err`.

### caplog: log records

```python
def test_rejected_update_is_logged(ecu, caplog):
    with caplog.at_level(logging.WARNING, logger="ecusim"):
        with pytest.raises(EcuError):
            ecu.install("0.5.0")

    assert caplog.record_tuples == [
        ("ecusim", logging.WARNING, "rejected 0.5.0: not newer than 1.0.0"),
    ]
```

`caplog.records` holds the `LogRecord` objects, `caplog.text` the formatted output, and `caplog.record_tuples` a list of `(logger, level, message)`. To watch logs live while tests run, use `pytest --log-cli-level=INFO`.

### Mocking with pytest-mock

`monkeypatch` swaps things. When you also need to assert how something was called, use `unittest.mock`. The pytest-mock plugin wraps it in a `mocker` fixture that undoes its patches automatically:

```python
def test_install_with_mocker(ecu, mocker):
    sleep = mocker.patch("ecusim.ecu.time.sleep")
    mocker.patch("ecusim.ecu.flash_delay", return_value=3.0)

    ecu.install("1.1.0")

    sleep.assert_called_once_with(3.0)
```

Mock at the boundary of your code (hardware, network, clock) and keep the logic in between real. A test that mocks everything only tests the mocks.

| Fixture | Controls |
| --- | --- |
| `tmp_path`, `tmp_path_factory` | Temporary directories |
| `monkeypatch` | Environment, attributes, dict items, cwd |
| `capsys`, `capfd` | stdout and stderr |
| `caplog` | Logging |
| `request` | Information about the requesting test |
| `pytestconfig` | Command-line options and config values |
| `cache` | Values kept between runs |
| `recwarn` | Warnings raised during the test |

### Exercise 6

1. Test that `load_fleet` raises `json.JSONDecodeError` for a file containing `not json`.
2. Test that a successful `install` logs `HU now runs 1.1.0` at INFO level. Hint: `caplog.at_level(logging.INFO, logger="ecusim")`.
3. `test_flash_delay_default` deletes a variable that the autouse `fast_flash` fixture set. Explain to yourself why that works. Hint: both use the same `monkeypatch` instance for that test.
4. *Stretch:* write a session-scoped fixture that creates one fleet file with `tmp_path_factory.mktemp("data")` and use it in two tests.

## Module 7: Configuration, plugins and hooks (25 min)

Project-wide settings live in one config file, extra features come from plugins, and you customise pytest itself with hook functions in `conftest.py`.

### Configuration

Replace the `[tool.pytest]` table in `pyproject.toml` with:

```toml
[tool.pytest]
minversion = "9.0"
testpaths = ["tests"]
addopts = ["-ra", "--strict-markers", "--strict-config"]
xfail_strict = true
markers = [
    "slow: takes more than a moment; deselect with -m 'not slow'",
    "hil: needs the real test bench; enable with --run-hil",
]
```

| Option | Effect |
| --- | --- |
| `testpaths` | Where a bare `pytest` looks for tests |
| `addopts` | Flags added to every run |
| `--strict-config` | A misspelled option in this file is an error, not a silent no-op |
| `xfail_strict` | Every `xfail` behaves as `strict=True` |
| `markers` | The registered custom markers |

pytest reads the first config file it finds, in this order: `pytest.toml`, `pytest.ini`, `pyproject.toml`, `tox.ini`, `setup.cfg`. It never merges two files. The directory of that file becomes the rootdir, shown in the header of every run.

### Plugins

A plugin is a pip package that pytest loads automatically once installed. You already installed three:

| Plugin | Command | What you get |
| --- | --- | --- |
| pytest-cov | `pytest --cov=ecusim --cov-report=term-missing` | Coverage per file, with the uncovered line numbers |
| pytest-xdist | `pytest -n auto` | Tests spread over all CPU cores |
| pytest-mock | none | The `mocker` fixture from module 6 |

Run both commands now. xdist only works reliably when tests are independent of each other, which is one more reason to keep state in function-scoped fixtures. Under xdist, a session-scoped fixture runs once per worker process, not once overall.

Other plugins worth knowing: pytest-timeout (kill hanging tests), pytest-rerunfailures (retry flaky tests), pytest-html (HTML report) and pytest-asyncio (async tests). For CI, `pytest --junitxml=report.xml` is built in and is read by Jenkins and GitHub Actions.

In a Jenkins or GitHub Actions job, pair that with the lockfile from module 0: `uv sync --locked`, then `uv run --no-sync pytest -n auto --junitxml=report.xml`. The job then tests exactly the plugin versions you tested locally.

### Hooks

Hooks are functions with fixed names starting with `pytest_` that pytest calls at defined points in a run. Put them in `conftest.py`. This pair adds a `--run-hil` flag and skips `hil` tests unless it is given. Add to `tests/conftest.py`:

```python
def pytest_addoption(parser):
    parser.addoption("--run-hil", action="store_true", help="run tests marked hil")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-hil"):
        return
    skip_hil = pytest.mark.skip(reason="needs --run-hil")
    for item in items:
        if "hil" in item.keywords:
            item.add_marker(skip_hil)
```

Run `pytest` and then `pytest --run-hil`. `test_on_real_bench` is skipped in the first run and executed in the second.

`pytest_addoption` registers the flag. `pytest_collection_modifyitems` receives every collected test after collection and may reorder, deselect or mark them. Inside a fixture, read the same option with `request.config.getoption("--run-hil")`.

| Hook | Called | Common use |
| --- | --- | --- |
| `pytest_addoption` | At startup | Add command-line flags |
| `pytest_configure` | After config is parsed | Global setup, register markers in code |
| `pytest_collection_modifyitems` | After collection | Skip, reorder or deselect tests |
| `pytest_runtest_setup` | Before each test | Per-test preconditions |
| `pytest_runtest_makereport` | After each test phase | Attach logs or screenshots on failure |
| `pytest_sessionfinish` | At the end | Write summaries, clean up |

A plugin is nothing more than a module of hooks and fixtures that is installed as a package. When several projects need the same `conftest.py`, that is the moment to turn it into a plugin.

### Exercise 7

1. Run coverage and confirm both source files are at 100 %. If not, the report tells you which lines to test.
2. Add `--durations=3` to `addopts`, run, then remove it.
3. Add an option `--ecu-name` with `default="HU"` and make the `ecu` fixture use it through `request.config.getoption`. Run `pytest --ecu-name TCU`.
4. *Stretch:* implement `pytest_report_header(config)` returning the string `"bench: simulated"` and find it in the run header.

## Module 8: Robot Framework with pytest-robotframework (40 min)

[pytest-robotframework](https://github.com/DetachHead/pytest-robotframework) is a third-party pytest plugin that does two things: it produces Robot Framework reports (`log.html`, `report.html`, `output.xml`) for tests written in Python, and it lets pytest collect and run `.robot` files. You keep pytest's fixtures, parametrization and plugins, and still deliver the Robot log that test managers and tools expect.

I assumed this plugin is the "Robot Framework extension" you meant. It is the maintained one on PyPI; tell me if you meant a different package.

### Install and configure

```bash
uv add --group robot pytest-robotframework typing-extensions
```

The plugin goes into its own `robot` dependency group, so it is locked with everything else but only installed when you ask for it. Run this module's commands as `uv run --group robot pytest ...`. Because `uv run` never removes packages, the plugin then stays in `.venv`; run `uv sync` to get back to the plain `dev` environment.

`typing-extensions` is listed explicitly because pytest-robotframework 4.6.3 imports it without declaring it as a dependency. In uv's clean environment the plugin fails with `ModuleNotFoundError: No module named 'typing_extensions'` without it. With plain pip you may never notice, because some other package usually pulled it in. An exact, locked environment exposes this kind of hidden dependency.

This also installs Robot Framework. The plugin activates itself. In `pyproject.toml`, add one marker and one option to the `[tool.pytest]` table:

```toml
markers = [
    "slow: takes more than a moment; deselect with -m 'not slow'",
    "hil: needs the real test bench; enable with --run-hil",
    "ota: over-the-air update behaviour",
]
enable_assertion_pass_hook = true
```

`enable_assertion_pass_hook` makes passing `assert` statements appear in the Robot log; without it only failing ones do.

### Python tests with a Robot log

Create `robot_tests/conftest.py`:

```python
import pytest
from robot.api import logger

from ecusim.ecu import Ecu


@pytest.fixture(autouse=True)
def fast_flash(monkeypatch):
    monkeypatch.setenv("ECUSIM_FLASH_DELAY", "0")


@pytest.fixture
def ecu():
    logger.info("connecting to HU")
    unit = Ecu("HU")
    unit.connect()
    yield unit
    logger.info("disconnecting from HU")
    unit.disconnect()
```

Create `robot_tests/test_ota.py`:

```python
import pytest
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from ecusim.ecu import Ecu, EcuError
from pytest_robotframework import AssertOptions, as_keyword, keyword


@keyword
def flash(ecu: Ecu, version: str) -> None:
    """Shows up as a keyword, with its arguments, in log.html."""
    logger.info(f"flashing {ecu.name} with {version}")
    ecu.install(version)


@pytest.mark.ota
def test_upgrade(ecu):
    flash(ecu, "1.1.0")
    assert ecu.firmware == "1.1.0", AssertOptions(description="firmware was updated")


@pytest.mark.ota
@pytest.mark.parametrize("version", ["0.9.0", "1.0.0"])
def test_downgrade_is_rejected(ecu, version):
    with pytest.raises(EcuError):
        flash(ecu, version)


def test_steps_and_robot_keywords(ecu):
    with as_keyword("check supply voltage"):
        voltage = ecu.read_voltage()
        BuiltIn().should_be_true(voltage > 11.5)
    with as_keyword("update twice"):
        flash(ecu, "1.1.0")
        flash(ecu, "1.2.0")
    assert ecu.firmware == "1.2.0"
```

Run it and open the log in a browser:

```bash
uv run --group robot pytest robot_tests --robot-outputdir results
```

What to look for in `results/log.html`:

- Each test has three top-level keywords: `Setup`, `Run Test` and `Teardown`. Fixture setup and teardown, with their `logger.info` lines, land in the first and last.
- `flash` appears as the keyword `Flash` with its arguments, because of `@keyword`. Import it from `pytest_robotframework`, not from `robot.api.deco`. Undecorated Python functions do not appear in the log.
- `as_keyword("...")` groups a block of lines into one named step.
- `pytest.raises` appears as a `Raises` keyword. The plugin patches most pytest functions this way.
- The `ota` marker became a Robot tag, and each parametrized case is its own test.
- `BuiltIn().should_be_true(...)` shows that you can call Robot library keywords from Python.

### Running .robot files through pytest

Robot tests call keywords from a library. Create `robot_tests/EcuLibrary.py`:

```python
"""A plain Robot Framework keyword library wrapping ecusim."""

from ecusim.ecu import Ecu


class EcuLibrary:
    ROBOT_LIBRARY_SCOPE = "TEST"

    def __init__(self) -> None:
        self.ecu: Ecu | None = None

    def connect_ecu(self, name: str, firmware: str = "1.0.0") -> None:
        self.ecu = Ecu(name, firmware)
        self.ecu.connect()

    def disconnect_ecu(self) -> None:
        self.ecu.disconnect()

    def install_firmware(self, version: str) -> None:
        self.ecu.install(version)

    def firmware_should_be(self, expected: str) -> None:
        if self.ecu.firmware != expected:
            raise AssertionError(f"firmware is {self.ecu.firmware}, expected {expected}")
```

Create `robot_tests/ota.robot`. Separate cells with at least two spaces:

```robotframework
*** Settings ***
Library             OperatingSystem
Library             EcuLibrary.py
Suite Setup         Set Environment Variable    ECUSIM_FLASH_DELAY    0
Test Setup          Connect Ecu    HU
Test Teardown       Disconnect Ecu

*** Test Cases ***
Upgrade Installs New Firmware
    [Tags]    ota
    Install Firmware    1.1.0
    Firmware Should Be    1.1.0

Downgrade Is Rejected
    [Tags]    ota    slow
    Run Keyword And Expect Error    *not newer*    Install Firmware    0.9.0
    Firmware Should Be    1.0.0
```

Run `pytest robot_tests -v --robot-outputdir results`. pytest now reports six tests, two of them from `ota.robot`, in one run and one log.

Three things I observed with plugin version 4.6.3 that are easy to trip over:

- Robot tags are converted to pytest markers. With `--strict-markers`, an unregistered tag fails collection, which is why you registered `ota`.
- The autouse `fast_flash` fixture did not apply to the `.robot` tests in my runs; without the `Suite Setup` line the upgrade test took the full 2 seconds. Do setup for `.robot` tests in Robot itself.
- Without `--robot-outputdir`, the three report files are written to the current directory on every run.

### Use pytest options, not Robot options

Selection and control go through pytest. The plugin docs list these equivalents ([configuration](https://detachhead.github.io/pytest-robotframework/4.6.2/configuration)):

| Instead of | Use |
| --- | --- |
| `robot --include ota` | `pytest -m ota` |
| `robot --exclude slow` | `pytest -m "not slow"` |
| `robot --test "Downgrade Is Rejected" ota.robot` | `pytest "robot_tests/ota.robot::Downgrade Is Rejected"` |
| `robot --exitonfailure` | `pytest --maxfail=1` |
| `robot --rerunfailed` | `pytest --lf` |
| `robot --dryrun` | `pytest --collect-only` (close, not identical) |

Other Robot options take a `--robot-` prefix, for example `pytest --robot-loglevel DEBUG:INFO`. `pytest --help` lists the supported ones. To set options in code, add this hook to `robot_tests/conftest.py`:

```python
from pytest_robotframework import RobotOptions


def pytest_robot_modify_options(options: RobotOptions, session: pytest.Session) -> None:
    if not session.config.option.collectonly:
        options["loglevel"] = "DEBUG:INFO"
```

The same hook is where you append Robot listeners with `options["listener"].append(...)`.

The plugin also works with pytest-xdist: `pytest robot_tests -n 2 --robot-outputdir results` runs in parallel and merges the results into one log.

### Limits to know

- Keywords that rely on Robot's continue-on-failure mechanism, such as `Run Keyword And Continue On Failure`, do not behave correctly when called from Python. The plugin docs recommend `pytest.raises` or `try`/`except` instead ([limitations](https://detachhead.github.io/pytest-robotframework/4.6.2/limitations)).
- Third-party functions do not show as keywords unless you wrap them once in `conftest.py` with `keywordify(module, "function_name")`.
- `logger.console` only prints when you run with `--capture=no`.
- If you ever disable the plugin with `-p no:robotframework` and see an `AttributeError` mentioning `_call_assertion_hook`, delete the `__pycache__` folders. I hit this once from stale cached test modules.

### Exercise 8

1. Run only the tests tagged `ota` and not `slow`. Confirm that selection covers both the Python and the `.robot` tests.
2. Make `test_upgrade` fail by expecting `1.1.1`. Open `log.html` and find the failed assertion with both values.
3. Add a keyword `Voltage Should Be Above` to `EcuLibrary` and a third `.robot` test that uses it.
4. *Stretch:* add `results/` to `.gitignore`, add `robot_tests` to `testpaths`, and run the whole project with a bare `pytest --robot-outputdir results`.

## Module 9: Capstone (30 min)

Build one new feature test-first: firmware rollback. Write the tests, watch them fail, then implement until they pass. No new code is given here; everything you need is in modules 1 to 8.

The specification:

- `Ecu.rollback()` restores the firmware version that was installed before the most recent successful update.
- It raises `EcuError` with a message containing `nothing to roll back` if no update has happened yet.
- It needs a connection, like `install`.
- It logs `rolled back to <version>` at INFO level on the `ecusim` logger.
- Only one level of rollback is kept. A second `rollback()` in a row raises `EcuError`.

Your checklist:

- [ ] Remove the `skip` marker from `test_rollback` in `test_markers.py`, move the test to a new file `tests/test_rollback.py`, and make it assert something real.
- [ ] Add a fixture `updated_ecu` to `conftest.py` that yields an ECU already updated from `1.0.0` to `1.1.0`.
- [ ] One test for the happy path using `updated_ecu`.
- [ ] One test with `pytest.raises(..., match=...)` for a rollback on a fresh ECU.
- [ ] One parametrized test over update chains, for example `["1.1.0"]`, `["1.1.0", "1.2.0"]` and `["1.1.0", "2.0.0", "2.0.1"]`, checking the version after one rollback. Give the cases readable ids.
- [ ] One test with `caplog` for the log message.
- [ ] One test for the double rollback.
- [ ] Run the tests and see them fail for the right reason, an `AttributeError`, before you write `rollback`.
- [ ] Implement `rollback` and get the suite green.
- [ ] Run `pytest --cov=ecusim --cov-report=term-missing` and close any gap in `ecu.py`.
- [ ] Add a `Rollback Firmware` keyword to `EcuLibrary` and one `.robot` test for it, then run the whole project with `pytest tests robot_tests --robot-outputdir results`.

You are done when the whole suite passes with `-n auto` as well. If it only passes without xdist, two tests share state somewhere.

## Pitfalls and next steps

These six mistakes account for most of the confusing pytest failures I would expect you to hit in the first weeks.

| Symptom | Cause | Fix |
| --- | --- | --- |
| `fixture 'x' not found` | Fixture lives in another test file, or `conftest.py` is in the wrong directory | Move it to a `conftest.py` at or above the test |
| `ScopeMismatch` | A wide-scoped fixture requests a function-scoped one | Narrow the outer scope, or use `tmp_path_factory` and similar session-level variants |
| Tests pass alone but fail together | Shared mutable state in a module, class or wide fixture | Build the state in a function-scoped fixture |
| A patch has no effect | Patched where the name is defined, not where it is used | Patch the module that looks the name up |
| `import file mismatch` or wrong module imported | Two test files with the same name and no packages | Give test files unique names |
| `ModuleNotFoundError` for your own package | Package not installed in the environment | `pip install -e .` |

Where to go next, in order of payoff for HiL and framework work:

1. [How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html): finalizers, fixture overriding per directory, and `request` in depth.
2. [Writing hook functions](https://docs.pytest.org/en/stable/how-to/writing_hook_functions.html) and [writing plugins](https://docs.pytest.org/en/stable/how-to/writing_plugins.html): how frameworks are built on top of pytest. The `pytester` fixture tests plugins themselves.
3. [Flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html): the pytest team's advice on causes and remedies.
4. [Good integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html): layouts and import modes for larger projects.
5. [pytest-robotframework API reference](https://detachhead.github.io/pytest-robotframework/pytest_robotframework.html): the full list of functions and hooks.

## Sources

Pages read for this tutorial on 13 November 2026:

- [pytest documentation, stable](https://docs.pytest.org/en/stable/)
- [pytest: configuration files and rootdir](https://docs.pytest.org/en/stable/reference/customize.html)
- [pytest: how to use subtests](https://docs.pytest.org/en/stable/how-to/subtests.html)
- [pytest-robotframework: features](https://detachhead.github.io/pytest-robotframework/4.6.2/features)
- [pytest-robotframework: configuration](https://detachhead.github.io/pytest-robotframework/4.6.2/configuration)
- [pytest-robotframework: limitations](https://detachhead.github.io/pytest-robotframework/4.6.2/limitations)
- [pytest-robotframework on PyPI](https://pypi.org/project/pytest-robotframework)

* [uv: locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
* [uv: project structure and files](https://docs.astral.sh/uv/concepts/projects/layout/)
* [uv: managing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/)

The rest comes from general pytest knowledge, checked by running every example.
