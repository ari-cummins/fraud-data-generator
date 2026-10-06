"""Base rates on the shipped configuration.

These are the numbers the detection rules are calibrated against. They are
asserted on the full dataset, not the small one, because the rates are
config-dependent -- a 300-customer run over one year produces noticeably
different ratios and would pin the wrong thing.

Bands are deliberately wider than the observed values. A tight band on a
stochastic quantity is a flaky test, and a flaky test gets ignored.
"""


def test_refund_share_of_transactions(full_dataset):
    data, _, _, _ = full_dataset
    refunds = [r for r in data.transactions if r["transaction_type"] in ("refund", "fee_waiver")]
    share = len(refunds) / len(data.transactions)
    assert 0.045 <= share <= 0.075, f"refunds were {share:.2%} of transactions"


def test_lookups_without_a_contact(full_dataset):
    """If this climbs too high, Rule 1 stops being a ranking problem."""
    data, _, _, _ = full_dataset
    no_contact = [r for r in data.crm_access if r["contact_id"] is None]
    share = len(no_contact) / len(data.crm_access)
    assert 0.010 <= share <= 0.030, f"{share:.2%} of lookups had no contact"


def test_most_agents_are_honest(full_dataset):
    _, workforce, _, _ = full_dataset
    share = len(workforce.dishonest_ids) / len(workforce.agents)
    assert 0.10 <= share <= 0.35, f"{share:.0%} of agents are offenders"


def test_protected_persons_are_a_small_minority(full_dataset):
    _, _, customers, _ = full_dataset
    share = len(customers.protected_ids) / len(customers.customers)
    assert 0.005 <= share <= 0.025, f"{share:.2%} of customers are protected"


def test_self_service_is_roughly_the_configured_share(full_dataset):
    data, _, _, cfg = full_dataset
    self_service = [r for r in data.contacts if r["channel"] == "self_service"]
    share = len(self_service) / len(data.contacts)
    assert abs(share - cfg.p_self_service) < 0.08, (
        f"self-service was {share:.1%}, configured {cfg.p_self_service:.0%}"
    )
