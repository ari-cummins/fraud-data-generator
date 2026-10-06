# Contact Centre Fraud — Synthetic Data Generator

[![tests](https://github.com/ari-cummins/fraud-data-generator/actions/workflows/tests.yml/badge.svg)](https://github.com/ari-cummins/fraud-data-generator/actions/workflows/tests.yml)

Generates seven relational tables of contact-centre activity for a fictional
Australian government service agency, with fraud planted in them.

**The design constraint: there are no fraud flags anywhere in the output.** No
`fraud_label`, no `scenario_type`, no `risk_score`. Every row is an ordinary
business record. Fraud exists only as a *pattern across rows*, which is what
makes the dataset usable for demonstrating detection logic rather than
demonstrating that a label column can be selected.

## Install

```bash
uv pip install -e ".[dev]"
```

Requires Python 3.11+. The only runtime dependency is pandas.

## Use

```bash
fraud-generate                                   # 7,500 customers, 3 years, to ./output
fraud-generate --seed 7 --out ./data             # different seed, different directory
fraud-generate --customers 500 --years 1         # a small dataset
fraud-generate --no-write                        # summary only, write nothing
fraud-generate --verbose                         # debug logging to stderr
```

Or as a library:

```python
from fraud_generator import Config, generate, build_tables, check_no_labels, write_tables

data, workforce, customers = generate(Config(seed=42, num_customers=500))
tables = build_tables(data, workforce, customers)
check_no_labels(tables)
write_tables(tables, "output")
```

Output is deterministic: the same `Config` always produces byte-identical CSVs.

## Output

| table | rows (default config) | grain |
|---|---|---|
| `agents` | 20 | one row per agent |
| `customers` | 7,500 | one row per customer |
| `contacts` | ~134,000 | one row per call or portal session |
| `crm_access` | ~151,000 | one row per record lookup |
| `transactions` | ~30,000 | one row per payment, refund or waiver |
| `profile_changes` | ~12,000 | one row per *field* changed |
| `auth_events` | ~79,000 | one row per login attempt |

## The three principles

**One code path.** A fraudulent CRM lookup is built by the same function as a
legitimate one. The builders in `builders.py` take no `fraud=True` parameter, so
a label cannot leak into a row even by accident.

**Hidden propensity.** A minority of agents carry a latent `_dishonest` marker
that steers which ordinary records get generated. It is dropped before export
and never reaches disk, and a guard rail fails the build if any column
resembling a label survives.

**Base rates.** Every artefact appearing in a fraud pattern also appears in
volume in legitimate activity — refunds, failed logins, after-hours access,
lookups with no call attached. No single column gives the answer away, so the
detection rules have to do real work.

## Planted patterns

| # | pattern | how it is findable |
|---|---|---|
| 1 | Unlawful locate | lookups with no matching call, ranked per agent |
| 2 | After-hours access | lookups more than an hour outside the rostered shift |
| 3 | Excessive lookups | >10 distinct customers viewed by one agent in one hour |
| 4 | Benefit fraud | refund or waiver with no prior purchase by that customer |
| 5 | Identity takeover | 3+ profile fields changed in one contact, ID document included |
| 6 | Account takeover | failed-login run from an unfamiliar IP, then success, then a valuable change |
| 7 | Post-termination access | lookups dated after the agent's termination |
| 8 | Collusion | agent pairs whose no-call lookup overlap exceeds what chance predicts for their volumes |

## Layout

```
src/fraud_generator/
  config.py     Config dataclass, validated at construction
  pools.py      reference data: names, addresses, teams, screens
  helpers.py    pure functions: timestamps, shifts, identifiers
  actors.py     Workforce and CustomerBase construction
  builders.py   Dataset — the five row builders and their shared state
  engine.py     one chronological pass; ordinary activity, then fraud
  detection.py  Rule 8 scoring — the one rule that needed tests
  export.py     DataFrame shaping, label guard rail, CSV writing
  cli.py        fraud-generate entry point
```

## Tests

```bash
pytest
```

96 tests, about 18 seconds, run in CI on Python 3.11 through 3.14. Four kinds:

- **Unit** — pure helpers, `Dataset` state, `Config` validation.
- **Structural** — referential integrity, no activity before an agent's hire date.
- **Scenario** — each of the eight patterns is actually present in the output,
  and the planted collusion pairs rank top by Rule 8's score. These are the
  ones that matter: the dataset's value is that the fraud is findable, and
  nothing else checks that.
- **Golden** — `test_reproducibility.py` pins SHA-256 fingerprints of all seven
  tables. A deliberate change to generation requires re-recording them with a
  note saying why.

The golden test is what made the package refactor safe: the notebook this grew
out of was converted to a package, had its config injected, and had its engine
decomposed, with byte-identical output proven at each step.

## Design notes

Built as a learning project, converted from a single notebook into an
installable package. Decisions worth knowing about:

- `Config` is frozen and passed explicitly rather than read as module globals,
  so tests can generate small datasets without touching the defaults.
- `random.seed()` is called once, at the top of `generate()`. Seeding at import
  time makes reproducibility depend on import order.
- Modules are safe to import: they define names and do nothing else.
- `write_tables` takes a directory, not a `Config` — a function's signature
  should state its real dependencies.
- The library logs and returns; `cli.py` is the only module that configures
  logging or writes to stdout.
