from datetime import datetime, timedelta

from dataclasses import dataclass, field

@dataclass(frozen=True)
class Config:
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

    # --- Legitimate base rates ---
    p_contact_has_transaction: float = 0.22
    p_contact_has_profile_change: float = 0.09
    p_txn_is_refund: float = 0.07
    p_legit_refund_has_purchase: float = 0.94
    p_legit_no_contact_access: float = 0.008
    p_legit_warm_transfer: float = 0.006
    p_legit_3_field_change: float = 0.015
    p_self_serve_failed_login: float = 0.14
    p_self_serve_lockout: float = 0.020

    # --- Hidden agent propensity ---
    p_agent_dishonest: float = 0.15
    p_agent_terminated: float = 0.11

    # --- Fraud pattern intensity ---
    locate_lookups_per_month: int = 12
    p_locate_after_hours: float = 0.35
    velocity_bursts_per_year: int = 3
    velocity_burst_size: tuple = (22, 40)
    benefit_fraud_per_month: int = 2
    identity_fraud_per_month: int = 1
    account_takeovers_per_month: int = 6
    post_termination_accesses: tuple = (3, 9)

    # --- Trend and calendar ---
    fraud_trend_yoy: float = 0.15
    shift_windows: dict = field(
        default_factory=lambda: {"day": (7, 15), "evening": (15, 23), "night": (23, 7)}
    )

    @property
    def total_days(self) -> int:
        return 365 * self.years

    @property
    def date_range(self) -> list:
        return [self.start_date + timedelta(days=i) for i in range(self.total_days)]


DEFAULT = Config()