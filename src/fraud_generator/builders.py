"""Row builders.

Every record in the dataset comes from one of these five methods. This is the
enforcement mechanism for the project's central constraint: legitimate and
fraudulent activity call the identical builder, differing only in arguments.
There is no `fraud=True` parameter to pass, so a label cannot leak into a row.

State lives on the instance rather than at module level, so one `Dataset` is
one independent dataset -- two can be built in the same process without their
ID sequences colliding.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime

from fraud_generator import helpers, pools

Row = dict[str, object]
Table = list[Row]


class Dataset:
    """Accumulates generated rows. One instance = one independent dataset."""

    def __init__(self) -> None:
        self.contacts: Table = []
        self.crm_access: Table = []
        self.transactions: Table = []
        self.profile_changes: Table = []
        self.auth_events: Table = []
        self._counters: defaultdict[str, int] = defaultdict(int)
        # customer_id -> timestamps of purchases/renewals. Not an output table:
        # a derived index the engine reads to decide whether a refund is honest.
        self.purchase_history: defaultdict[str, list[datetime]] = defaultdict(list)

    def _next_id(self, prefix: str) -> str:
        self._counters[prefix] += 1
        return helpers.seq_id(prefix, self._counters[prefix])

    def add_contact(
        self,
        ts: datetime,
        channel: str,
        customer_id: str,
        agent_id: str | None = None,
        queue: str | None = None,
        duration: int | None = None,
    ) -> str:
        cid = self._next_id("CON")
        self.contacts.append({
            "contact_id": cid,
            "contact_timestamp": ts.isoformat(sep=" "),
            "channel": channel,
            "customer_id": customer_id,
            "agent_id": agent_id,
            "queue": queue or (random.choice(pools.QUEUES) if channel == "agent_assisted" else "self_service"),
            "ivr_path": random.choice(pools.IVR_PATHS) if channel == "agent_assisted" else "portal>self_service",
            "duration_seconds": duration or (
                random.randint(90, 1100) if channel == "agent_assisted" else random.randint(40, 420)
            ),
            "disposition": random.choices(pools.DISPOSITIONS, weights=[0.60, 0.13, 0.12, 0.10, 0.05])[0],
            "authentication_method": random.choices(
                ["knowledge_based", "document_verification", "digital_id", "none"],
                weights=[0.55, 0.24, 0.18, 0.03])[0],
        })
        return cid

    def add_access(
        self,
        ts: datetime,
        agent_id: str,
        customer_id: str,
        contact_id: str | None,
        screens: list[str],
    ) -> str:
        aid = self._next_id("ACC")
        self.crm_access.append({
            "access_id": aid,
            "access_timestamp": ts.isoformat(sep=" "),
            "agent_id": agent_id,
            "customer_id": customer_id,
            "contact_id": contact_id,  # NULL when there was no call in progress
            "screens_viewed": "|".join(screens),
            "records_returned": random.randint(1, 3),
            "access_channel": "crm_desktop",
        })
        return aid

    def add_transaction(
        self,
        ts: datetime,
        customer_id: str,
        txn_type: str,
        amount: float,
        agent_id: str | None,
        contact_id: str | None,
        channel: str,
    ) -> str:
        tid = self._next_id("TXN")
        self.transactions.append({
            "transaction_id": tid,
            "transaction_timestamp": ts.isoformat(sep=" "),
            "customer_id": customer_id,
            "transaction_type": txn_type,
            "amount_aud": round(amount, 2),
            "agent_id": agent_id,
            "contact_id": contact_id,
            "channel": channel,
            "payment_method": random.choice(["card", "bpay", "direct_debit", "voucher"]),
        })
        if txn_type in ("purchase", "renewal"):
            self.purchase_history[customer_id].append(ts)
        return tid

    def add_profile_change(
        self,
        ts: datetime,
        customer_id: str,
        fields: list[str],
        agent_id: str | None,
        contact_id: str | None,
        channel: str,
    ) -> None:
        """Writes one row per field changed -- the only builder that is not 1:1."""
        for field in fields:
            self.profile_changes.append({
                "change_id": self._next_id("CHG"),
                "change_timestamp": ts.isoformat(sep=" "),
                "customer_id": customer_id,
                "field_changed": field,
                "previous_value": "REDACTED",
                "new_value": "REDACTED",
                "agent_id": agent_id,
                "contact_id": contact_id,
                "channel": channel,
            })

    def add_auth_event(
        self,
        ts: datetime,
        customer_id: str,
        event_type: str,
        ip: str | None = None,
        ua: str | None = None,
    ) -> None:
        self.auth_events.append({
            "auth_event_id": self._next_id("AUT"),
            "event_timestamp": ts.isoformat(sep=" "),
            "customer_id": customer_id,
            "event_type": event_type,
            "source_ip": ip or helpers.ip_address(),
            "user_agent": ua or random.choice(pools.USER_AGENTS),
            "channel": "self_service_portal",
        })
