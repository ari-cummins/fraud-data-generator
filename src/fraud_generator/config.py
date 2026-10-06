"""Generation parameters.

Every knob lives here. `Config` is frozen and passed explicitly to the
functions that need it, rather than read as module globals, so that tests can
generate small datasets without touching the defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


class ConfigError(ValueError):
    """Raised when a Config is constructed with values that cannot generate."""


#: Four distinct offenders are needed to form the two collusion pairs, and
#: build_workforce spins forever if it cannot reach that many.
MIN_AGENTS = 4


@dataclass(frozen=True)
class Config:
    """Parameters for one generation run.

    The fields split into three groups, and the split is the design: volume
    knobs set the size of the dataset, legitimate base rates decide how much
    innocent activity looks superficially like fraud, and fraud intensity
    decides how much real offending is planted. The detection rules are only
    non-trivial because the second group exists.
    """

    seed: int = 42
    output_dir: str = "output"

    # --- Volume ---
    num_customers: int = 7500
    num_agents: int = 20
    contacts_per_day: int = 150
    years: int = 3
    start_date: datetime = datetime(2023, 1, 1)

    # --- Channel mix ---
    p_self_service: float = 0.45

    # --- Legitimate base rates (these are what stop the rules being trivial) ---
    p_contact_has_transaction: float = 0.22
    p_contact_has_profile_change: float = 0.09
    p_txn_is_refund: float = 0.07
    p_legit_refund_has_purchase: float = 0.94
    p_legit_no_contact_access: float = 0.008
    p_legit_warm_transfer: float = 0.006
    p_legit_3_field_change: float = 0.015
    p_self_serve_failed_login: float = 0.14
    p_self_serve_lockout: float = 0.020

    # --- Hidden agent propensity (never exported) ---
    p_agent_dishonest: float = 0.20
    p_agent_terminated: float = 0.11

    # --- Fraud pattern intensity ---
    locate_lookups_per_month: int = 12
    p_locate_after_hours: float = 0.35
    velocity_bursts_per_year: int = 3
    velocity_burst_size: tuple[int, int] = (22, 40)
    benefit_fraud_per_month: int = 2
    identity_fraud_per_month: int = 1
    account_takeovers_per_month: int = 6
    post_termination_accesses: tuple[int, int] = (3, 9)

    # --- Trend and calendar ---
    fraud_trend_yoy: float = 0.15
    shift_windows: dict[str, tuple[int, int]] = field(
        default_factory=lambda: {"day": (7, 15), "evening": (15, 23), "night": (23, 7)}
    )

    def __post_init__(self) -> None:
        """Fail at construction rather than halfway through a generation run."""
        if self.num_customers < 1:
            raise ConfigError(f"num_customers must be positive, got {self.num_customers}")
        if self.num_agents < MIN_AGENTS:
            # Not cosmetic: build_workforce loops `while len(dishonest) < n_bad`
            # drawing from range(num_agents), and n_bad has a floor of 4 so that
            # two collusion pairs can be formed. With fewer than 4 agents the
            # set can never reach n_bad and the loop never terminates.
            raise ConfigError(
                f"num_agents must be at least {MIN_AGENTS}, got {self.num_agents}: "
                "the generator plants two collusion pairs, which needs four "
                "distinct offenders"
            )
        if self.contacts_per_day < 1:
            raise ConfigError(f"contacts_per_day must be positive, got {self.contacts_per_day}")
        if self.years < 1:
            raise ConfigError(f"years must be at least 1, got {self.years}")

        for name, value in vars(self).items():
            if name.startswith("p_") and not 0.0 <= value <= 1.0:
                raise ConfigError(f"{name} must be a probability in [0, 1], got {value}")

        for name in ("velocity_burst_size", "post_termination_accesses"):
            low, high = getattr(self, name)
            if low > high:
                raise ConfigError(f"{name} must be (low, high) with low <= high, got {(low, high)}")

    @property
    def total_days(self) -> int:
        return 365 * self.years

    @property
    def date_range(self) -> list[datetime]:
        """Every day in the generation window.

        Rebuilt on each access, so bind it to a local before looping over it.
        """
        return [self.start_date + timedelta(days=i) for i in range(self.total_days)]


DEFAULT = Config()
