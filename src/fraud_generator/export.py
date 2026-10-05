"""Shaping generated rows into tables and writing them to disk.

Three separable jobs, kept separate so that only one of them touches the
filesystem: `build_tables` and `check_no_labels` are pure and testable without
a temp directory; `write_tables` is the only function that writes.
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from fraud_generator import config
from fraud_generator.actors import CustomerBase, Workforce
from fraud_generator.builders import Dataset

logger = logging.getLogger(__name__)

#: Substrings that must never appear in an exported column name. The whole
#: premise of the dataset is that fraud exists only as a pattern across rows,
#: so a column carrying the answer would defeat it.
BANNED = ("fraud", "label", "scenario", "suspicious", "anomal", "is_bad", "risk_score")

Tables = dict[str, pd.DataFrame]


class LabelLeakError(Exception):
    """Raised when a column that could reveal the answer reached the output."""


def build_tables(data: Dataset, workforce: Workforce, customers: CustomerBase) -> Tables:
    """Shape generated rows into the seven export tables, hidden columns dropped."""
    return {
        "agents": pd.DataFrame(workforce.agents).drop(columns=["_dishonest", "_termination_dt"]),
        "customers": pd.DataFrame(customers.customers),
        "contacts": pd.DataFrame(data.contacts).sort_values("contact_timestamp"),
        "crm_access": pd.DataFrame(data.crm_access).sort_values("access_timestamp"),
        "transactions": pd.DataFrame(data.transactions).sort_values("transaction_timestamp"),
        "profile_changes": pd.DataFrame(data.profile_changes).sort_values("change_timestamp"),
        "auth_events": pd.DataFrame(data.auth_events).sort_values("event_timestamp"),
    }


def check_no_labels(tables: Tables) -> None:
    """Fail loudly if a label or an internal column reached the output.

    Raises rather than asserts: assertions are stripped under `python -O`, and
    this guard rail is the one check that must survive every way of running the
    package.
    """
    for name, df in tables.items():
        for col in df.columns:
            if any(b in col.lower() for b in BANNED):
                raise LabelLeakError(f"label leak: {name}.{col}")
            if col.startswith("_"):
                raise LabelLeakError(f"internal column exported: {name}.{col}")


def write_tables(tables: Tables, output_dir: str) -> list[str]:
    """Write each table to <output_dir>/<name>.csv. Returns the paths written."""
    os.makedirs(output_dir, exist_ok=True)
    written = []
    for name, df in tables.items():
        path = os.path.join(output_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        written.append(path)
        logger.debug("wrote %s (%d rows)", path, len(df))
    logger.info("wrote %d tables to %s/", len(written), output_dir)
    return written


def format_summary(tables: Tables, cfg: config.Config) -> str:
    """Render row counts and headline base rates as text.

    Returns a string rather than printing, so the caller decides where it goes.
    Library code should not own the terminal.
    """
    lines = [f"{len(tables)} tables generated - no fraud labels present", ""]
    for name, df in tables.items():
        lines.append(f"  {name:<18} {len(df):>8,} rows  x {len(df.columns):>2} cols")

    txns = tables["transactions"]
    access = tables["crm_access"]
    auth = tables["auth_events"]
    refunds = txns["transaction_type"].isin(["refund", "fee_waiver"])
    no_contact = access["contact_id"].isna()
    date_range = cfg.date_range

    lines += [
        "",
        f"  Period             {date_range[0].date()} to {date_range[-1].date()}",
        f"  Refunds/waivers    {refunds.sum():,} ({refunds.mean():.1%} of transactions)",
        f"  Access w/o contact {no_contact.sum():,} ({no_contact.mean():.1%} of lookups)",
        f"  Failed logins      {(auth['event_type'] == 'failed_login').sum():,}",
    ]
    return "\n".join(lines)
