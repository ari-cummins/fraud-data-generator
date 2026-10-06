# Known issues

No open issues.

## Fixed

### Rule 8 could not separate collusion from high-volume offending (fixed 2026-10-06)

Rule 8 ranked agent pairs by the raw count of customers they had both looked up
with no call in progress. That count is dominated by how much each agent looks
up at all. Every offender draws unlawful-locate targets from the same
7,500-customer pool, and a velocity burst adds 22–40 lookups in a single hour,
so two busy offenders overlap heavily without ever having colluded.

At the shipped config the raw ranking put a pair that never colluded first,
sharing 137 customers against a chance expectation of 78. A planted pair came
second on 106 against an expectation of 38, and the other planted pair came
fourth. The rule was largely restating Rule 1 — "these agents do a lot of
no-call lookups" — rather than detecting a relationship between them.

Fixed by scoring the *excess over chance* instead of the raw count. For two
agents who looked up `n1` and `n2` distinct customers out of `N`, overlap under
independent sampling is hypergeometric:

```
expected = n1 * n2 / N
variance = n1 * (n2/N) * (1 - n2/N) * (N - n1) / (N - 1)
z        = (observed - expected) / sqrt(variance)
```

Ranked by `z`, the two planted pairs come **first and second of 190**, with
11.9 and 11.0 against 8.2 for the next pair. Pairs sharing fewer than three
customers are dropped: their expected overlap is near zero, so a single
coincidence produces a large ratio on no evidence.

The data was never the problem — the analytic was. No generator change was
needed and the golden fingerprints are unaffected.

The scoring lives in `fraud_generator/detection.py` rather than in a notebook
cell, with unit tests in `tests/test_detection.py` pinning both the behaviour
and the reason for it, including a test asserting that the top pair by raw
count is *not* a planted pair — so if that ever stops being true, the simpler
rule can come back.

### `collusion_pairs` was always empty (fixed 2026-10-05)

`n_bad = max(3, int(num_agents * p_agent_dishonest))` produced 3 offenders at
the default config, while the collusion block required `len(bad_ids) >= 4`. The
guard was never satisfied, so no collusion was planted in any dataset the
project ever generated, and Rule 8's output was entirely coincidental overlap.

Fixed by raising `p_agent_dishonest` to 0.20 and the floor to 4. The floor
matters independently: with a floor of 3, any config where
`num_agents * p_agent_dishonest < 4` silently produced no collusion, which is
how the bug survived.

### Missing `contact_id` read from CSV is `NaN`, not `None` (fixed 2026-10-06)

`collusion_pair_scores` originally tested `contact_id is None`. Rows straight
out of the generator carry `None`, but the same rows read back from CSV with
pandas carry `NaN`, which is neither `None` nor equal to itself. The rule would
have scored zero pairs on exactly the path the analysis notebook uses.

### Label guard rail only checked one column per table (fixed 2026-09-12)

The internal-column assertion sat outside the per-column loop, so it tested
whichever column happened to be last. An internal `_`-prefixed column anywhere
else would have been exported.

### `assert` used for the label guard rail (fixed 2026-10-05)

Assertions are stripped under `python -O`. The guard now raises `LabelLeakError`
so it survives every way of running the package.
