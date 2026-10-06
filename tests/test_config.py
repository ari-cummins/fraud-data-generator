"""Config validation. A bad config should fail at construction, not mid-run."""

import pytest

from fraud_generator.config import Config, ConfigError


@pytest.mark.parametrize(
    "kwargs, expected_fragment",
    [
        ({"num_customers": 0}, "num_customers"),
        ({"num_customers": -5}, "num_customers"),
        ({"num_agents": 0}, "num_agents"),
        ({"num_agents": 1}, "at least 4"),
        ({"num_agents": 2}, "at least 4"),
        ({"num_agents": 3}, "at least 4"),
        ({"contacts_per_day": 0}, "contacts_per_day"),
        ({"years": 0}, "years"),
        ({"p_self_service": 1.5}, "probability"),
        ({"p_self_service": -0.1}, "probability"),
        ({"p_agent_dishonest": 2.0}, "probability"),
        ({"velocity_burst_size": (40, 22)}, "low <= high"),
        ({"post_termination_accesses": (9, 3)}, "low <= high"),
    ],
)
def test_invalid_config_raises(kwargs, expected_fragment):
    with pytest.raises(ConfigError) as exc:
        Config(**kwargs)
    assert expected_fragment in str(exc.value)


def test_four_agents_is_the_smallest_workable_config():
    """Regression: fewer than four agents hung build_workforce forever.

    n_bad has a floor of 4 so two collusion pairs can be formed, and the loop
    that picks offenders draws from range(num_agents) until it has n_bad
    distinct ones. With three agents it could never get there.
    """
    cfg = Config(num_customers=10, num_agents=4, years=1, contacts_per_day=1)
    assert cfg.total_days == 365
    assert len(cfg.date_range) == 365


def test_config_is_frozen(cfg):
    with pytest.raises(Exception):
        cfg.num_customers = 10


def test_derived_values_follow_their_inputs():
    assert Config(years=2).total_days == 730
    assert len(Config(years=2).date_range) == 730
