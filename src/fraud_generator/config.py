from datetime import datetime, timedelta

SEED = 42
OUTPUT_DIR = "output"

# --- Volume -----------------------------------------------------------------
NUM_CUSTOMERS = 7500
NUM_AGENTS = 20
CONTACTS_PER_DAY = 150
YEARS = 3
START_DATE = datetime(2023, 1, 1)

# --- Channel mix ------------------------------------------------------------
P_SELF_SERVICE = 0.45

# --- Legitimate base rates (these are what stop the rules from being trivial) -
P_CONTACT_HAS_TRANSACTION = 0.22   # contacts that produce a transaction
P_CONTACT_HAS_PROFILE_CHANGE = 0.09  # contacts that update the customer record
P_TXN_IS_REFUND = 0.07             # refunds/waivers as a share of transactions
P_LEGIT_REFUND_HAS_PURCHASE = 0.94  # honest refunds nearly always follow a purchase
P_LEGIT_NO_CONTACT_ACCESS = 0.008   # QA review, callback prep, complaint handling
P_LEGIT_WARM_TRANSFER = 0.006       # agent opens a different customer, legitimately
P_LEGIT_3_FIELD_CHANGE = 0.015      # honest bulk update (new identity documents)
P_SELF_SERVE_FAILED_LOGIN = 0.14    # sessions with 1-2 fumbled password attempts
P_SELF_SERVE_LOCKOUT = 0.020        # honest sessions with 3+ failures then success

# --- Hidden agent propensity (never exported) --------------------------------
P_AGENT_DISHONEST = 0.15    # share of agents who will offend
P_AGENT_TERMINATED = 0.11   # share of agents who leave during the window

# --- Fraud pattern intensity -------------------------------------------------
LOCATE_LOOKUPS_PER_MONTH = 12      # unlawful locate events per dishonest agent
P_LOCATE_AFTER_HOURS = 0.35        # of those, share done outside rostered shift
VELOCITY_BURSTS_PER_YEAR = 3       # excessive-lookup episodes per dishonest agent
VELOCITY_BURST_SIZE = (22, 40)     # customers pulled in a single hour
BENEFIT_FRAUD_PER_MONTH = 2        # bogus refunds/waivers per dishonest agent
IDENTITY_FRAUD_PER_MONTH = 1       # takeover-at-the-counter events per agent
ACCOUNT_TAKEOVERS_PER_MONTH = 6    # external self-service takeovers, agency-wide
POST_TERMINATION_ACCESSES = (3, 9) # lookups by a leaver after their last day

# --- Year-on-year growth in offending ----------------------------------------
FRAUD_TREND_YOY = 0.15

# --- Business calendar --------------------------------------------------------
SHIFT_WINDOWS = {"day": (7, 15), "evening": (15, 23), "night": (23, 7)}

TOTAL_DAYS = 365 * YEARS
DATE_RANGE = [START_DATE + timedelta(days=i) for i in range(TOTAL_DAYS)]


## Initial global variables to parse through other files
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