"""Rule 8: scoring agent pairs for collusion.

The headline test is that the planted pairs come out on top at the shipped
config. The unit tests below pin the reason it works -- that the score is an
excess over chance, not a raw count.
"""

import pytest

from fraud_generator.detection import collusion_pair_scores


def _access(agent, customer, contact_id=None):
    return {"agent_id": agent, "customer_id": customer, "contact_id": contact_id}


# ------------------------------------------------------------------ the real thing


def test_planted_pairs_rank_top_at_the_shipped_config(full_dataset):
    """The property the naive raw-count version of this rule did not have."""
    data, workforce, customers, _ = full_dataset
    scores = collusion_pair_scores(data.crm_access, len(customers.ids))
    planted = {tuple(sorted(pair)) for pair in workforce.collusion_pairs}

    top = {s.pair for s in scores[: len(planted)]}
    assert top == planted, (
        f"expected the planted pairs {planted} to be the top {len(planted)} "
        f"by excess overlap; got {top}"
    )


def test_a_clear_margin_separates_planted_from_the_rest(full_dataset):
    """Ranking first is not enough if it is first by a hair."""
    data, workforce, customers, _ = full_dataset
    scores = collusion_pair_scores(data.crm_access, len(customers.ids))
    n = len(workforce.collusion_pairs)
    assert scores[n - 1].z > scores[n].z * 1.2, (
        f"planted pairs scored {scores[n - 1].z:.2f}, next best {scores[n].z:.2f} "
        "- too close to call collusion apart from coincidence"
    )


def test_raw_count_alone_would_not_have_worked(full_dataset):
    """Why the rule changed, pinned as a test.

    The pair with the highest raw shared-customer count is not a planted pair.
    If this ever stops being true the normalisation is no longer earning its
    keep and the simpler rule could come back.
    """
    data, workforce, customers, _ = full_dataset
    scores = collusion_pair_scores(data.crm_access, len(customers.ids))
    planted = {tuple(sorted(pair)) for pair in workforce.collusion_pairs}
    by_raw_count = max(scores, key=lambda s: s.shared)
    assert by_raw_count.pair not in planted


# ------------------------------------------------------------------------- units


def test_volume_is_discounted():
    """Same raw overlap, different volumes: the quieter pair is more suspicious."""
    population = 1000
    rows = []
    # Quiet pair: 20 lookups each, 10 shared. Expected overlap 0.4.
    rows += [_access("quiet_a", f"C{i}") for i in range(20)]
    rows += [_access("quiet_b", f"C{i}") for i in range(10, 30)]
    # Busy pair: 200 lookups each, also 10 shared. Expected overlap 40.
    rows += [_access("busy_a", f"D{i}") for i in range(200)]
    rows += [_access("busy_b", f"D{i}") for i in range(190, 390)]

    scores = {s.pair: s for s in collusion_pair_scores(rows, population)}
    quiet = scores[("quiet_a", "quiet_b")]
    busy = scores[("busy_a", "busy_b")]

    assert quiet.shared == busy.shared == 10
    assert quiet.z > busy.z
    assert busy.z < 0  # busy pair overlaps *less* than chance predicts


def test_lookups_attached_to_a_call_are_ignored():
    """Rule 8 is about lookups with no call in progress."""
    rows = [_access("a", f"C{i}", contact_id="CON-1") for i in range(50)]
    rows += [_access("b", f"C{i}", contact_id="CON-2") for i in range(50)]
    assert collusion_pair_scores(rows, 1000) == []


def test_nan_contact_id_counts_as_no_call():
    """Rows read back from CSV carry NaN, not None, for a missing contact_id.

    Checking only for None scored zero pairs on the CSV path, which is the path
    the analysis notebook uses.
    """
    nan = float("nan")
    rows = [
        {"agent_id": "a", "customer_id": f"C{i}", "contact_id": nan} for i in range(20)
    ] + [
        {"agent_id": "b", "customer_id": f"C{i}", "contact_id": nan} for i in range(20)
    ]
    scores = collusion_pair_scores(rows, 1000)
    assert len(scores) == 1
    assert scores[0].shared == 20


def test_min_shared_drops_coincidences():
    rows = [_access("a", "C1"), _access("a", "C2"), _access("b", "C1")]
    assert collusion_pair_scores(rows, 1000) == []
    scored = collusion_pair_scores(rows, 1000, min_shared=1)
    assert len(scored) == 1 and scored[0].shared == 1


def test_results_are_sorted_most_significant_first():
    rows = []
    rows += [_access("a", f"C{i}") for i in range(30)]
    rows += [_access("b", f"C{i}") for i in range(30)]          # 30 shared
    rows += [_access("c", f"C{i}") for i in range(5)]           # 5 shared with a, b
    scores = collusion_pair_scores(rows, 2000)
    assert [s.z for s in scores] == sorted((s.z for s in scores), reverse=True)


def test_duplicate_lookups_count_once():
    """The rule is about distinct customers, not lookup volume."""
    rows = [_access("a", "C1")] * 40 + [_access("b", "C1")] * 40
    scores = collusion_pair_scores(rows, 1000, min_shared=1)
    assert scores[0].shared == 1
    assert scores[0].n_first == scores[0].n_second == 1


@pytest.mark.parametrize("population", [0, 1, -3])
def test_impossible_population_is_rejected(population):
    with pytest.raises(ValueError, match="population"):
        collusion_pair_scores([], population)
