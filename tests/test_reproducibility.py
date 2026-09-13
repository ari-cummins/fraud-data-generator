import hashlib
import json

import pytest

from fraud_generator.engine import generate

# Fingerprints of the dataset at SEED=42, verified byte-identical to the
# original notebook on 2026-09-12. Any change here means generation changed.
EXPECTED = {
    "agents": ("0a5cd9a9c4040c2453505bee978c529ffeebfb9edeef6e34d6925b0c4e011cf9", 20),
    "customers": ("eedf2c4693177760d395f82c9c7664b1126f6c53cd7a3718fddda13fb9ca9453", 7500),
    "contacts": ("9e8a1ca077d64555b5797f1b3faf5214e9756c57d7cc282591e8532b44ce0529", 133992),
    "crm_access": ("2eb3c00a169c6b256b73a58917a94fb7dae06fc2feb23693c5b3adb91da9d4b1", 149645),
    "transactions": ("54b9f56f022c802c63d58443d4da6280cc91d54de9c1ecc62cf4505fe47635f2", 29557),
    "profile_changes": ("f432a36bd2b9eae592e150772790ded889975896a657d05850e691848d4c3713", 12186),
    "auth_events": ("4c05dd85e5fd24579cd68e15bfee6e9c76d02349158147354a89cdb51afc9ebf", 79184),
}


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()


@pytest.mark.slow
def test_generation_matches_golden_fingerprint():
    data, workforce, customers = generate()
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
        assert len(rows) == expected_count, f"{name}: row count changed"
        assert fingerprint(rows) == expected_hash, f"{name}: contents changed"