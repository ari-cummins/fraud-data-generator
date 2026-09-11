import random
from datetime import timedelta

from fraud_generator import config, pools

def full_name():
    return f"{random.choice(pools.FIRST_NAMES)} {random.choice(pools.LAST_NAMES)}"


def street_address():
    suburb, state, postcode = random.choice(pools.SUBURBS)
    return f"{random.randint(1, 320)} {random.choice(pools.STREETS)}", suburb, state, postcode


def mobile_number():
    return f"04{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}"


def date_of_birth():
    days = random.randint(18 * 365, 88 * 365)
    return (config.START_DATE - timedelta(days=days)).date().isoformat()


def ip_address(residential=True):
    if residential:
        return f"{random.choice([49, 58, 60, 101, 120, 139])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"{random.choice([45, 91, 185, 194, 212])}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def seq_id(prefix, n):
    return f"{prefix}-{n:08d}"


def in_shift(hour, shift):
    """Is this hour inside the agent's rostered window?"""
    start, end = config.SHIFT_WINDOWS[shift]
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end  # night shift wraps midnight


def shift_hour(shift):
    """Draw an hour from inside a rostered shift window."""
    start, end = config.SHIFT_WINDOWS[shift]
    hours = list(range(start, end)) if start < end else list(range(start, 24)) + list(range(0, end))
    return random.choice(hours)


def stamp(day, hour=None, shift="day"):
    hour = shift_hour(shift) if hour is None else hour
    return day.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))


def year_weight(day_index):
    """Offending grows year on year; returns a multiplier for that day's rate."""
    return (1 + config.FRAUD_TREND_YOY) ** (day_index // 365)