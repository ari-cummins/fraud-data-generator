"""Properties of the generated dataset.

Two kinds of assertion here. Structural tests check the data is coherent --
no dangling foreign keys, no activity before an agent was hired. Scenario
tests check that each planted fraud pattern actually exists in the output.

The second kind is the point of this file. The generator's whole value
proposition is that the fraud is findable; without these tests a pattern can
silently stop being planted and every other test still passes. That is exactly
how the collusion bug survived undetected.
"""

import statistics
from collections import defaultdict
from datetime import datetime


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


# ------------------------------------------------------------------- structural


def test_every_access_contact_id_exists(small_dataset):
    """A null contact_id is legitimate; a dangling one is not."""
    data, _, _, _ = small_dataset
    contact_ids = {row["contact_id"] for row in data.contacts}
    for row in data.crm_access:
        cid = row["contact_id"]
        assert cid is None or cid in contact_ids


def test_every_customer_id_exists(small_dataset):
    data, _, customers, _ = small_dataset
    known = {c["customer_id"] for c in customers.customers}
    tables = {
        "contacts": data.contacts,
        "crm_access": data.crm_access,
        "transactions": data.transactions,
        "profile_changes": data.profile_changes,
        "auth_events": data.auth_events,
    }
    for name, rows in tables.items():
        unknown = {r["customer_id"] for r in rows} - known
        assert not unknown, f"{name} references {len(unknown)} unknown customers"


def test_every_agent_id_exists(small_dataset):
    data, workforce, _, _ = small_dataset
    known = {a["agent_id"] for a in workforce.agents}
    for row in data.crm_access:
        assert row["agent_id"] in known


def test_no_access_before_the_agent_was_hired(small_dataset):
    data, workforce, _, _ = small_dataset
    hired = {a["agent_id"]: _parse(a["hire_date"]) for a in workforce.agents}
    early = [
        row for row in data.crm_access
        if _parse(row["access_timestamp"]) < hired[row["agent_id"]]
    ]
    assert not early, f"{len(early)} lookups predate the agent's hire date"


def test_contacts_are_inside_the_generation_window(small_dataset):
    data, _, _, cfg = small_dataset
    first, last = cfg.date_range[0], cfg.date_range[-1]
    for row in data.contacts:
        ts = _parse(row["contact_timestamp"])
        assert first <= ts <= last.replace(hour=23, minute=59, second=59)


# --------------------------------------------------------------------- scenarios


def test_unlawful_locate_is_planted(small_dataset):
    """Rule 1: offenders rank far above the honest pack on no-contact lookups."""
    data, workforce, _, _ = small_dataset
    dishonest = set(workforce.dishonest_ids)
    per_agent = defaultdict(int)
    for row in data.crm_access:
        if row["contact_id"] is None:
            per_agent[row["agent_id"]] += 1

    offender_counts = [per_agent[a] for a in dishonest]
    honest_counts = [n for a, n in per_agent.items() if a not in dishonest] or [0]
    assert min(offender_counts) > max(honest_counts), (
        "offenders should outrank every honest agent on no-contact lookups: "
        f"offenders {sorted(offender_counts)}, honest max {max(honest_counts)}"
    )


def test_after_hours_lookups_are_planted(small_dataset):
    """Rule 2: some offending happens outside the agent's rostered window."""
    data, workforce, _, cfg = small_dataset
    from fraud_generator import helpers

    after_hours = [
        row for row in data.crm_access
        if not helpers.in_shift(
            _parse(row["access_timestamp"]).hour,
            workforce.by_id[row["agent_id"]]["shift_pattern"],
            cfg,
        )
    ]
    assert after_hours, "no after-hours lookups were planted"


def test_velocity_bursts_are_planted(small_dataset):
    """Rule 3: an agent views an implausible number of customers in one hour."""
    data, _, _, _ = small_dataset
    per_agent_hour = defaultdict(set)
    for row in data.crm_access:
        bucket = (row["agent_id"], row["access_timestamp"][:13])
        per_agent_hour[bucket].add(row["customer_id"])
    biggest = max(len(v) for v in per_agent_hour.values())
    assert biggest > 10, f"largest agent-hour was only {biggest} distinct customers"


def test_refunds_without_prior_purchase_are_planted(small_dataset):
    """Rule 4: benefit fraud -- a refund for a customer who never paid."""
    data, _, _, _ = small_dataset
    first_purchase = {}
    for row in data.transactions:
        if row["transaction_type"] in ("purchase", "renewal"):
            ts = _parse(row["transaction_timestamp"])
            cid = row["customer_id"]
            if cid not in first_purchase or ts < first_purchase[cid]:
                first_purchase[cid] = ts

    orphans = [
        row for row in data.transactions
        if row["transaction_type"] in ("refund", "fee_waiver")
        and (row["customer_id"] not in first_purchase
             or _parse(row["transaction_timestamp"]) < first_purchase[row["customer_id"]])
    ]
    assert orphans, "no refund without a prior purchase was planted"


def test_bulk_identity_rewrites_are_planted(small_dataset):
    """Rule 5: 3+ fields changed in one contact, including the ID document."""
    data, _, _, _ = small_dataset
    by_contact = defaultdict(set)
    for row in data.profile_changes:
        by_contact[row["contact_id"]].add(row["field_changed"])
    bulk = [fields for fields in by_contact.values()
            if len(fields) >= 3 and "identity_document" in fields]
    assert bulk, "no bulk identity rewrite was planted"


def test_honest_bulk_updates_exist_as_near_misses(small_dataset):
    """Rule 5's precision depends on these: 3+ fields changed, no ID document.

    If these stopped being generated the rule would look perfect, and would be
    worthless -- it would be a label wearing a costume.
    """
    data, _, _, _ = small_dataset
    by_contact = defaultdict(set)
    for row in data.profile_changes:
        by_contact[row["contact_id"]].add(row["field_changed"])
    near_misses = [fields for fields in by_contact.values()
                   if len(fields) >= 3 and "identity_document" not in fields]
    assert near_misses, "no honest bulk updates to act as near-misses"


def test_account_takeovers_are_planted(small_dataset):
    """Rule 6: a run of failed logins from one IP, then a success."""
    data, _, _, _ = small_dataset
    by_customer = defaultdict(list)
    for row in sorted(data.auth_events, key=lambda r: r["event_timestamp"]):
        by_customer[row["customer_id"]].append(row)

    takeovers = 0
    for events in by_customer.values():
        run = 0
        run_ip = None
        for ev in events:
            if ev["event_type"] == "failed_login":
                run = run + 1 if ev["source_ip"] == run_ip else 1
                run_ip = ev["source_ip"]
            elif ev["event_type"] == "login_success":
                if run >= 4 and ev["source_ip"] == run_ip:
                    takeovers += 1
                run, run_ip = 0, None
    assert takeovers, "no external account takeover was planted"


def test_post_termination_access_is_planted(small_dataset):
    """Rule 7: a departed officer's credentials are still live."""
    data, workforce, _, _ = small_dataset
    terminated = {
        a["agent_id"]: a["_termination_dt"]
        for a in workforce.agents
        if a["_termination_dt"] is not None
    }
    late = [
        row for row in data.crm_access
        if row["agent_id"] in terminated
        and _parse(row["access_timestamp"]) > terminated[row["agent_id"]]
    ]
    assert late, "no post-termination access was planted"


def test_collusion_pairs_are_planted_and_rank_highly(small_dataset):
    """Rule 8: the planted pairs must stand out on shared no-contact lookups.

    This is the test that would have caught the bug where `n_bad` was 3 but the
    collusion guard needed 4, so no collusion was ever generated and Rule 8 was
    quietly firing on coincidental overlap between busy offenders instead.

    KNOWN LIMITATION, deliberately encoded here rather than hidden: the planted
    pairs rank near the top but are not guaranteed to BE the top. All offenders
    draw their unlawful-locate targets from the same customer pool, so two
    high-volume offenders who never colluded can share more customers by chance
    than a planted pair does by design. At the shipped config the planted pairs
    rank 2nd and 4th of 190. Rule 8 is therefore a ranking signal that needs
    Rule 1 alongside it, not a standalone collusion detector -- see
    docs/known-issues.md.
    """
    data, workforce, _, _ = small_dataset
    assert len(workforce.collusion_pairs) >= 2, "no collusion pairs were created"

    seen = defaultdict(set)
    for row in data.crm_access:
        if row["contact_id"] is None:
            seen[row["agent_id"]].add(row["customer_id"])

    shared = {}
    agents = sorted(seen)
    for i, a1 in enumerate(agents):
        for a2 in agents[i + 1:]:
            shared[(a1, a2)] = len(seen[a1] & seen[a2])

    planted = {tuple(sorted(pair)) for pair in workforce.collusion_pairs}
    ranked = sorted(shared, key=shared.get, reverse=True)
    positions = [i + 1 for i, pair in enumerate(ranked) if tuple(sorted(pair)) in planted]
    median = statistics.median(shared.values())

    top_fifth = max(len(ranked) // 5, len(planted))
    assert positions, "planted pairs produced no shared no-contact lookups at all"
    assert max(positions) <= top_fifth, (
        f"planted pairs ranked {positions} of {len(ranked)} pairs; "
        f"expected all within the top {top_fifth}"
    )
    for pair in planted:
        assert shared[pair] > median, (
            f"planted pair {pair} shared {shared[pair]} customers, "
            f"no better than the median pair ({median})"
        )
