import os

import pandas as pd

BANNED = ("fraud", "label", "scenario", "suspicious", "anomal", "is_bad", "risk_score")


def build_tables(data, workforce, customers):
    """Shape generated rows into the seven export tables."""
    df_agents = pd.DataFrame(workforce.agents).drop(columns=["_dishonest", "_termination_dt"])
    df_customers = pd.DataFrame(customers.customers)
    df_contacts = pd.DataFrame(data.contacts).sort_values("contact_timestamp")
    df_access = pd.DataFrame(data.crm_access).sort_values("access_timestamp")
    df_transactions = pd.DataFrame(data.transactions).sort_values("transaction_timestamp")
    df_changes = pd.DataFrame(data.profile_changes).sort_values("change_timestamp")
    df_auth = pd.DataFrame(data.auth_events).sort_values("event_timestamp")

    tables = {
        "agents": df_agents,
        "customers": df_customers,
        "contacts": df_contacts,
        "crm_access": df_access,
        "transactions": df_transactions,
        "profile_changes": df_changes,
        "auth_events": df_auth,
    }
    return tables


def check_no_labels(tables):
    """Fail loudly if a label or internal column reached the output."""
    for name, df in tables.items():
        for col in df.columns:
            assert not any(b in col.lower() for b in BANNED), f"label leak: {name}.{col}"
            assert not col.startswith("_"), f"internal column exported: {name}.{col}"


def write_tables(tables, output_dir):
    """Write each table to <output_dir>/<name>.csv."""
    os.makedirs(output_dir, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(os.path.join(output_dir, f"{name}.csv"), index=False)


def print_summary(tables, cfg):
    """Print row/column counts and the headline base rates."""
    print(f"Written to {cfg.output_dir}/  — no fraud labels present\n")
    for name, df in tables.items():
        print(f"  {name:<18} {len(df):>8,} rows  x {len(df.columns):>2} cols")

    txns = tables["transactions"]
    access = tables["crm_access"]
    auth = tables["auth_events"]
    refunds = txns["transaction_type"].isin(["refund", "fee_waiver"])
    date_range = cfg.date_range

    print(f"\n  Period            {date_range[0].date()} to {date_range[-1].date()}")
    print(f"  Refunds/waivers   {refunds.sum():,} ({refunds.mean():.1%} of transactions)")
    print(f"  Access w/o contact {access['contact_id'].isna().sum():,} "
          f"({access['contact_id'].isna().mean():.1%} of lookups)")
    print(f"  Failed logins     {(auth['event_type'] == 'failed_login').sum():,}")
