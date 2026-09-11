from datetime import datetime, timedelta

import os
import random
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd

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

random.seed(SEED)