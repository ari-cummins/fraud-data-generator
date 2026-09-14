import pytest
import re

from fraud_generator import config, helpers, pools
from datetime import datetime

@pytest.fixture
def cfg():
    return config.DEFAULT

def test_seq_id_pads_to_eight_digits():
    assert helpers.seq_id("CUS", 1) == "CUS-00000001"
    assert helpers.seq_id("AGT", 20) == "AGT-00000020"

@pytest.mark.parametrize(
    "hour, shift, expected",
    [
        (9, "day", True),
        (7, "day", True),        # window is [start, end)
        (15, "day", False),      # end is exclusive
        (2, "day", False),
        (18, "evening", True),
        (23, "night", True),     # night wraps midnight
        (3, "night", True),
        (6, "night", True),
        (7, "night", False),
        (12, "night", False),
    ],
)
def test_in_shift(hour, shift, expected, cfg):
    assert helpers.in_shift(hour, shift, cfg) is expected


def test_shift_hour_always_lands_inside_the_window(cfg):
    for _ in range(200):
        hour = helpers.shift_hour("night", cfg)
        assert helpers.in_shift(hour, "night", cfg)

def test_mobile_number():
    for _ in range(200):
        number = helpers.mobile_number()
        assert re.fullmatch(r"04\d{2} \d{3} \d{3}", number)

def test_date_of_birth_in_plausible_range(cfg):
    for _ in range(200):
        birthdate = datetime.fromisoformat(helpers.date_of_birth(cfg))
        delta = cfg.start_date - birthdate
        assert 18 * 365 <= delta.days <= 88 * 365

def test_street_address():
    for _ in range(200):
        address = helpers.street_address()
        assert len(address) == 4
        assert address[1:] in pools.SUBURBS

def test_year_weight_steps_at_year_boundaries(cfg):
    assert helpers.year_weight(0, cfg) == 1.0
    assert helpers.year_weight(364, cfg) == 1.0          # still year 0
    assert helpers.year_weight(365, cfg) == pytest.approx(1.15)
    assert helpers.year_weight(800, cfg) == pytest.approx(1.15 ** 2)