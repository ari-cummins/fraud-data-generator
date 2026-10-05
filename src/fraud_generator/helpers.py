"""Small pure functions used throughout generation.

Names and addresses are assembled from independent component pools, so the
combination space is the product of the pools rather than the size of any one
of them -- that is what keeps 7,500 customers from looking repetitive.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from fraud_generator import config, pools


def full_name() -> str:
    return f"{random.choice(pools.FIRST_NAMES)} {random.choice(pools.LAST_NAMES)}"


def street_address() -> tuple[str, str, str, str]:
    """Returns (street line, suburb, state, postcode)."""
    suburb, state, postcode = random.choice(pools.SUBURBS)
    return f"{random.randint(1, 320)} {random.choice(pools.STREETS)}", suburb, state, postcode


def mobile_number() -> str:
    return f"04{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"


def date_of_birth(cfg: config.Config) -> str:
    """An ISO date between 18 and 88 years before the generation start date.

    Uses 365-day years, not calendar years -- the drift is immaterial for
    synthetic data and the tests assert this contract in its own units.
    """
    days = random.randint(18 * 365, 88 * 365)
    return (cfg.start_date - timedelta(days=days)).date().isoformat()


def ip_address(residential: bool = True) -> str:
    """A plausible IPv4. Non-residential prefixes stand in for hosting ranges."""
    if residential:
        first = random.choice([49, 58, 60, 101, 120, 139])
    else:
        first = random.choice([45, 91, 185, 194, 212])
    return f"{first}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def seq_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:08d}"


def in_shift(hour: int, shift: str, cfg: config.Config) -> bool:
    """Is this hour inside the agent's rostered window?

    Windows are half-open [start, end). The night shift wraps midnight, which
    is the only branch here with real logic in it.
    """
    start, end = cfg.shift_windows[shift]
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def shift_hour(shift: str, cfg: config.Config) -> int:
    """Draw an hour from inside a rostered shift window."""
    start, end = cfg.shift_windows[shift]
    hours = list(range(start, end)) if start < end else list(range(start, 24)) + list(range(0, end))
    return random.choice(hours)


def stamp(day: datetime, cfg: config.Config, hour: int | None = None, shift: str = "day") -> datetime:
    """Place a timestamp inside a given day, in-shift unless an hour is given."""
    hour = shift_hour(shift, cfg) if hour is None else hour
    return day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


def year_weight(day_index: int, cfg: config.Config) -> float:
    """Offending grows year on year; returns a multiplier for that day's rate.

    A step function, not a ramp: constant within a year, jumping at each
    365-day boundary.
    """
    return (1 + cfg.fraud_trend_yoy) ** (day_index // 365)
