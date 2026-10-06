"""Detection logic that needs to be tested rather than written once in a cell.

Most of the eight rules are a single filter or group-by and live in the
analysis notebook, where they belong. Rule 8 is here because the obvious
version of it is wrong, and a wrong rule that nobody tests is how the
collusion bug stayed hidden: the rule produced a plausible-looking ranking
from a dataset that contained no collusion at all.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable, Mapping, NamedTuple


def _no_call_in_progress(value: object) -> bool:
    """Was this lookup unattached to a call?

    Handles both representations. Rows straight out of the generator carry
    `None`; the same rows read back from CSV with pandas carry `NaN`, which is
    not equal to itself and is not `None`. Checking only for `None` silently
    scores zero pairs on the CSV path -- which is the path the analysis
    notebook uses.
    """
    return value is None or value != value


class PairScore(NamedTuple):
    """How much two agents' no-contact lookups overlap, against chance."""

    pair: tuple[str, str]
    shared: int
    expected: float
    z: float
    n_first: int
    n_second: int


def collusion_pair_scores(
    access_rows: Iterable[Mapping[str, object]],
    population: int,
    min_shared: int = 3,
) -> list[PairScore]:
    """Rank agent pairs by excess overlap in lookups with no call in progress.

    Pass rows as mappings -- a list of dicts, or `df.to_dict("records")`.
    `population` is the number of customers the agents could have looked up.

    Why not just count shared customers, which is the obvious rule? Because the
    count is dominated by how much each agent looks up at all. Two offenders
    each making several hundred unlawful locates across the same customer base
    overlap heavily by chance: at the shipped config the highest raw count
    belongs to a pair that never colluded, while a real pair sits second.
    Ranking on the raw count therefore mostly restates Rule 1.

    So compare each pair's overlap to what chance predicts for two agents of
    those volumes, and divide by the standard deviation of that quantity. Under
    independent sampling the overlap is hypergeometric with

        expected  = n1 * n2 / N
        variance  = n1 * (n2/N) * (1 - n2/N) * (N - n1) / (N - 1)

    `z` is how many standard deviations the observed overlap sits above
    expectation. That normalisation is what separates designed collusion from
    two busy offenders: a pair sharing 137 of an expected 78 is less remarkable
    than a pair sharing 44 of an expected 10.

    `min_shared` drops pairs with a handful of lookups between them. Their
    expected overlap is near zero, so one coincidence produces a large ratio
    on no evidence at all.

    Returns every qualifying pair, most significant first.
    """
    if population < 2:
        raise ValueError(f"population must be at least 2, got {population}")

    seen: defaultdict[str, set[str]] = defaultdict(set)
    for row in access_rows:
        if _no_call_in_progress(row.get("contact_id")):
            seen[str(row["agent_id"])].add(str(row["customer_id"]))

    scores: list[PairScore] = []
    agents = sorted(seen)
    for i, first in enumerate(agents):
        for second in agents[i + 1:]:
            n1, n2 = len(seen[first]), len(seen[second])
            shared = len(seen[first] & seen[second])
            if shared < min_shared:
                continue
            expected = n1 * n2 / population
            variance = n1 * (n2 / population) * (1 - n2 / population) \
                * (population - n1) / (population - 1)
            z = (shared - expected) / math.sqrt(variance) if variance > 0 else 0.0
            scores.append(PairScore((first, second), shared, expected, z, n1, n2))

    return sorted(scores, key=lambda s: s.z, reverse=True)
