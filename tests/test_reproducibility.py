"""The golden test: generation output must not drift.

Fingerprints recorded 2026-10-05, after the collusion fix raised
`p_agent_dishonest` to 0.20 and the `n_bad` floor to 4. The previous baseline
(recorded 2026-09-13) was verified byte-identical to the original notebook;
these values differ from it only by that deliberate change.

Why a recorded fingerprint rather than "the same seed twice gives the same
result": a self-consistency test passes even when a refactor changes every
value in the dataset, as long as it changes them consistently. Only a pinned
baseline catches that. This is what made the config injection and the engine
decomposition safe to do.

If this test fails and you did not intend to change generation, something
moved a `random` call. If you did intend it, recompute the values below with:

    python -c "import hashlib, json; from fraud_generator.engine import generate; \
      d, w, c = generate(); \
      [print(f'{n}: {hashlib.sha256(json.dumps(r, default=str).encode()).hexdigest()} {len(r)}') \
       for n, r in [('agents', w.agents), ('customers', c.customers), ('contacts', d.contacts), \
                    ('crm_access', d.crm_access), ('transactions', d.transactions), \
                    ('profile_changes', d.profile_changes), ('auth_events', d.auth_events)]]"

and say in the commit message why they changed.
"""

import hashlib
import json

EXPECTED = {
    "agents": ("b014ed09ea7b7e02b7ad9d5aa2c6330b9c8daa51240c3235dca812e1d468a8d3", 20),
    "customers": ("5e175f85a91078074e7b9e9549b94d62195b670777ed6b3f9192e7f920fb7ca5", 7500),
    "contacts": ("8c0b3fca0a37575629e45485ded35cc11b4772c536c135d24aa6afabe402d88d", 134117),
    "crm_access": ("671fe717a27aba8f1ddb485729ba6588929654ece361d8ec9a142c677f6f9943", 150716),
    "transactions": ("3765a4ed27116ec02207da10a56573548216e00e4bd79b39e39a63cfaa6be3f8", 29719),
    "profile_changes": ("8c0787679b1ff7abff0fea73b891e3856e61122cba30a8fa2ee9359c175d3f5e", 12356),
    "auth_events": ("d14dd8d0e3db877a486d0f4d22e138f0d16395cfe8c88ed288ee65c7372ac957", 79051),
}


def fingerprint(rows) -> str:
    # No sort_keys: dict key order decides CSV column order, so a reordering is
    # a real change and the fingerprint should catch it.
    return hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()


def test_generation_matches_golden_fingerprint(full_dataset):
    data, workforce, customers, _ = full_dataset
    actual = {
        "agents": workforce.agents,
        "customers": customers.customers,
        "contacts": data.contacts,
        "crm_access": data.crm_access,
        "transactions": data.transactions,
        "profile_changes": data.profile_changes,
        "auth_events": data.auth_events,
    }
    for name, (expected_hash, expected_count) in EXPECTED.items():
        rows = actual[name]
        # Asserted separately so the failure says whether the change was
        # structural (row count) or in the values (hash).
        assert len(rows) == expected_count, f"{name}: row count changed"
        assert fingerprint(rows) == expected_hash, f"{name}: contents changed"
