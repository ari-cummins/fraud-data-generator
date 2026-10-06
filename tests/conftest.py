"""Shared fixtures.

Two datasets are available. `small_dataset` generates in well under a second
and is what structural and scenario tests use. `full_dataset` is the shipped
configuration -- about three seconds -- and is used where the assertion is
genuinely about the production dataset, such as base rates and the golden
fingerprints.

Both are session-scoped: generated once and shared. Tests that use them must
only read, never mutate.
"""

import pytest

from fraud_generator import config
from fraud_generator.engine import generate


@pytest.fixture
def cfg():
    """The shipped configuration, for unit tests that just need some config."""
    return config.DEFAULT


@pytest.fixture(scope="session")
def small_cfg():
    """Small enough to generate in about a second, large enough to stay honest.

    `contacts_per_day` stays at the production value deliberately. The
    legitimate no-contact lookup rate is `int(volume * 0.008)`, so at 60
    contacts/day that rounds to zero and honest agents make no unattached
    lookups at all -- which would let the Rule 1 test pass against a column of
    zeros. Shrink the customer base and the window instead.
    """
    return config.Config(num_customers=400, num_agents=8, years=1, contacts_per_day=150)


@pytest.fixture(scope="session")
def small_dataset(small_cfg):
    data, workforce, customers = generate(small_cfg)
    return data, workforce, customers, small_cfg


@pytest.fixture(scope="session")
def full_dataset():
    data, workforce, customers = generate(config.DEFAULT)
    return data, workforce, customers, config.DEFAULT
