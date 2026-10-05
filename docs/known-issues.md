# Known issues

## Rule 8 cannot separate collusion from high-volume offending

**Status:** open, by design for now.

Colluding pairs are planted: two pairs of dishonest agents pull the same
customers on the same day, neither of them on a call, firing at `0.04 * trend`
per pair per day.

They do not reliably rank *first* on shared no-contact lookups. At the shipped
configuration the planted pairs rank 2nd and 4th out of 190 agent pairs, and
the top-ranked pair is two offenders who never colluded.

The cause is that every offender draws unlawful-locate targets from the same
7,500-customer pool. Two offenders each making several hundred lookups overlap
substantially by chance, and a velocity burst adds 22-40 more in a single hour.
Planted collusion contributes roughly 40-110 shared customers over three years;
coincidental overlap between two busy offenders reaches 137.

So Rule 8 as written partly restates Rule 1 — "both of these agents do an
unusual volume of no-contact lookups". It is a useful ranking signal next to
Rule 1, not a standalone collusion detector, and the notebook's claim that
"two people don't coincidentally browse the same strangers' records on the same
days" is not supported by the data as generated.

`tests/test_dataset.py::test_collusion_pairs_are_planted_and_rank_highly`
encodes the property that actually holds: planted pairs land in the top fifth
of pairs and share more customers than the median pair.

**Options if this is worth fixing:**

1. Give each colluding pair a small dedicated target list (say 60 customers)
   that they return to repeatedly, instead of sampling the whole population.
   This is also closer to how real collusion looks — a shared interest in
   specific people — and would concentrate the overlap enough to dominate the
   noise.
2. Raise the collusion firing rate by roughly 3x.
3. Add a second condition to Rule 8: shared customers *and* temporal proximity
   between the two agents' lookups, which the generator already produces (the
   second agent's access lands 5–180 minutes after the first).

Option 1 is the most defensible, and option 3 costs nothing in the generator.
Both change the dataset, so both invalidate the golden fingerprints in
`tests/test_reproducibility.py` and need a deliberate re-baseline.

## Fixed

### `collusion_pairs` was always empty (fixed 2026-10-05)

`n_bad = max(3, int(num_agents * p_agent_dishonest))` produced 3 offenders at
the default config, while the collusion block required `len(bad_ids) >= 4`. The
guard was never satisfied, so no collusion was planted in any dataset the
project ever generated, and Rule 8's output was entirely coincidental overlap.

Fixed by raising `p_agent_dishonest` to 0.20 and the floor to 4. The floor
matters independently: with a floor of 3, any config where
`num_agents * p_agent_dishonest < 4` silently produced no collusion, which is
how the bug survived.

### Label guard rail only checked one column per table (fixed 2026-09-12)

The internal-column assertion sat outside the per-column loop, so it tested
whichever column happened to be last. An internal `_`-prefixed column anywhere
else would have been exported.

### `assert` used for the label guard rail (fixed 2026-10-05)

Assertions are stripped under `python -O`. The guard now raises `LabelLeakError`
so it survives every way of running the package.
