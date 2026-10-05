"""The activity engine: one chronological pass over the generation window.

Each day, ordinary business runs first and plants the noise that keeps the
detection rules honest -- legitimate warm transfers, QA lookups with no call
attached, honest bulk profile updates, password fumbles. Fraud is then layered
on top by the same row builders, so no row can carry a label.

The phases are called in a fixed order and each consumes random numbers from a
single seeded stream. Changing the number or order of `random` calls anywhere
below changes every value drawn after it; `tests/test_reproducibility.py`
pins the result.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import NamedTuple

from fraud_generator import config, helpers, pools
from fraud_generator.actors import CustomerBase, Workforce, build_customers, build_workforce
from fraud_generator.builders import Dataset

logger = logging.getLogger(__name__)

Agent = dict[str, object]


class GenerationResult(NamedTuple):
    """What one generation run produced. Unpacks as a 3-tuple."""

    data: Dataset
    workforce: Workforce
    customers: CustomerBase


def generate(cfg: config.Config | None = None) -> GenerationResult:
    """Generate one complete dataset.

    Deterministic for a given `cfg.seed`: the same config always produces
    byte-identical output.
    """
    cfg = config.DEFAULT if cfg is None else cfg
    random.seed(cfg.seed)

    date_range = cfg.date_range
    logger.info(
        "generating %d customers, %d agents, %d days (seed=%d)",
        cfg.num_customers, cfg.num_agents, cfg.total_days, cfg.seed,
    )

    workforce = build_workforce(cfg)
    customers = build_customers(cfg)
    data = Dataset()

    logger.debug(
        "workforce: %d agents, %d dishonest, %d collusion pairs",
        len(workforce.agents), len(workforce.dishonest_ids), len(workforce.collusion_pairs),
    )

    for day_index, day in enumerate(date_range):
        roster = workforce.active_on(day)
        if not roster:
            continue

        weekday = day.weekday() < 5
        volume = int(cfg.contacts_per_day * (1.0 if weekday else 0.35))
        trend = helpers.year_weight(day_index, cfg)

        _ordinary_activity(data, cfg, customers, roster, day, volume)
        _unattached_lookups(data, cfg, customers, roster, day, volume)
        _insider_activity(data, cfg, customers, roster, day, trend)
        _collusion(data, cfg, customers, workforce, roster, day, trend)
        _external_takeover(data, cfg, customers, day, trend)

        if day_index and day_index % 365 == 0:
            logger.debug("year %d complete: %d contacts so far", day_index // 365, len(data.contacts))

    _post_termination_access(data, cfg, customers, workforce, date_range)

    logger.info(
        "generated %d contacts, %d lookups, %d transactions, %d profile changes, %d auth events",
        len(data.contacts), len(data.crm_access), len(data.transactions),
        len(data.profile_changes), len(data.auth_events),
    )
    return GenerationResult(data, workforce, customers)


# --------------------------------------------------------------- ordinary business


def _ordinary_activity(
    data: Dataset,
    cfg: config.Config,
    customers: CustomerBase,
    roster: list[Agent],
    day: datetime,
    volume: int,
) -> None:
    """A day's legitimate contacts, agent-assisted and self-service."""
    for _ in range(volume):
        customer_id = random.choice(customers.ids)
        agent_assisted = random.random() > cfg.p_self_service

        if agent_assisted:
            _agent_assisted_contact(data, cfg, customers, roster, day, customer_id)
        else:
            _self_service_contact(data, cfg, day, customer_id)


def _agent_assisted_contact(
    data: Dataset,
    cfg: config.Config,
    customers: CustomerBase,
    roster: list[Agent],
    day: datetime,
    customer_id: str,
) -> None:
    agent = random.choice(roster)
    ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
    contact_id = data.add_contact(ts, "agent_assisted", customer_id, agent["agent_id"])

    # The lookups that go with the call -- pretext satisfied. An agent typically
    # opens two or three screens while handling one contact.
    for _ in range(random.randint(1, 3)):
        data.add_access(
            ts + timedelta(seconds=random.randint(0, 600)),
            agent["agent_id"], customer_id, contact_id,
            random.sample(list(pools.FIELD_GROUPS), k=random.randint(1, 3)),
        )

    # Legitimate warm transfer: agent opens a second customer's record.
    if random.random() < cfg.p_legit_warm_transfer:
        data.add_access(
            ts + timedelta(minutes=random.randint(1, 6)), agent["agent_id"],
            random.choice(customers.ids), contact_id, ["profile", "contact"],
        )

    if random.random() < cfg.p_contact_has_transaction:
        if random.random() < cfg.p_txn_is_refund:
            # Honest refunds overwhelmingly follow a real purchase.
            if data.purchase_history[customer_id] and random.random() < cfg.p_legit_refund_has_purchase:
                data.add_transaction(
                    ts, customer_id, random.choice(["refund", "fee_waiver"]),
                    random.uniform(25, 320), agent["agent_id"], contact_id, "agent_assisted",
                )
        else:
            data.add_transaction(
                ts, customer_id, random.choice(["purchase", "renewal"]),
                random.uniform(20, 450), agent["agent_id"], contact_id, "agent_assisted",
            )

    if random.random() < cfg.p_contact_has_profile_change:
        data.add_profile_change(
            ts, customer_id, _honest_changed_fields(cfg),
            agent["agent_id"], contact_id, "agent_assisted",
        )


def _honest_changed_fields(cfg: config.Config) -> list[str]:
    """Which fields an honest profile update touches.

    An honest bulk update is a change of circumstances -- new address, new
    phone, new email. It never rewrites the identity document or bank account
    in the same breath, which is what buys Rule 5 its precision.
    """
    if random.random() < cfg.p_legit_3_field_change:
        return random.sample(
            ["residential_address", "postal_address", "mobile_phone", "email", "preferred_name"], 3
        )
    if random.random() < 0.30:
        return ["residential_address", "postal_address"]
    return [random.choice(pools.PROFILE_FIELDS)]


def _self_service_contact(
    data: Dataset, cfg: config.Config, day: datetime, customer_id: str
) -> None:
    ts = helpers.stamp(day, cfg, hour=random.randint(6, 23))
    ip = helpers.ip_address()
    ua = random.choice(pools.USER_AGENTS)

    # Honest people mistype their password all the time. This is why a run of
    # failed logins is not by itself evidence of a takeover.
    if random.random() < cfg.p_self_serve_lockout:
        n_fail = random.randint(3, 5)
    elif random.random() < cfg.p_self_serve_failed_login:
        n_fail = random.randint(1, 2)
    else:
        n_fail = 0
    for k in range(n_fail):
        data.add_auth_event(ts - timedelta(minutes=n_fail - k), customer_id, "failed_login", ip, ua)
    data.add_auth_event(ts, customer_id, "login_success", ip, ua)

    contact_id = data.add_contact(ts, "self_service", customer_id)

    if random.random() < cfg.p_contact_has_transaction:
        if random.random() < cfg.p_txn_is_refund and data.purchase_history[customer_id]:
            data.add_transaction(
                ts, customer_id, "refund", random.uniform(25, 200), None, contact_id, "self_service"
            )
        else:
            data.add_transaction(
                ts, customer_id, random.choice(["purchase", "renewal"]),
                random.uniform(20, 450), None, contact_id, "self_service",
            )

    if random.random() < cfg.p_contact_has_profile_change * 0.5:
        data.add_profile_change(
            ts, customer_id, [random.choice(pools.PROFILE_FIELDS)], None, contact_id, "self_service"
        )


def _unattached_lookups(
    data: Dataset,
    cfg: config.Config,
    customers: CustomerBase,
    roster: list[Agent],
    day: datetime,
    volume: int,
) -> None:
    """Legitimate lookups with no call attached.

    QA sampling, callback prep, complaint handling. These are why "no
    contact_id" is not itself damning, and why Rule 1 has to rank rather than
    simply flag.
    """
    for _ in range(int(volume * cfg.p_legit_no_contact_access)):
        agent = random.choice(roster)
        data.add_access(
            helpers.stamp(day, cfg, shift=agent["shift_pattern"]), agent["agent_id"],
            random.choice(customers.ids), None, ["profile"],
        )


# ------------------------------------------------------------ driven by propensity


def _insider_activity(
    data: Dataset,
    cfg: config.Config,
    customers: CustomerBase,
    roster: list[Agent],
    day: datetime,
    trend: float,
) -> None:
    """Offending by agents carrying the hidden `_dishonest` marker."""
    for agent in roster:
        if not agent["_dishonest"]:
            continue
        aid = agent["agent_id"]
        _unlawful_locate(data, cfg, customers, agent, aid, day, trend)
        _velocity_burst(data, cfg, customers, agent, aid, day, trend)
        _benefit_fraud(data, cfg, customers, agent, aid, day, trend)
        _identity_takeover(data, cfg, customers, agent, aid, day, trend)


def _unlawful_locate(
    data: Dataset, cfg: config.Config, customers: CustomerBase,
    agent: Agent, aid: str, day: datetime, trend: float,
) -> None:
    """(A) Looking up people with no business reason, some of it after hours."""
    if random.random() >= (cfg.locate_lookups_per_month * trend) / 30:
        return
    target = (
        random.choice(customers.protected_ids)
        if (customers.protected_ids and random.random() < 0.35)
        else random.choice(customers.ids)
    )
    if random.random() < cfg.p_locate_after_hours:
        hours = [h for h in range(24) if not helpers.in_shift(h, agent["shift_pattern"], cfg)]
        ts = helpers.stamp(day, cfg, hour=random.choice(hours))
    else:
        ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
    data.add_access(ts, aid, target, None, ["contact", "linked", "profile"])


def _velocity_burst(
    data: Dataset, cfg: config.Config, customers: CustomerBase,
    agent: Agent, aid: str, day: datetime, trend: float,
) -> None:
    """(B) A burst of unrelated records pulled inside one hour."""
    if random.random() >= (cfg.velocity_bursts_per_year * trend) / 365:
        return
    base = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
    for _ in range(random.randint(*cfg.velocity_burst_size)):
        data.add_access(
            base + timedelta(minutes=random.randint(0, 55)), aid,
            random.choice(customers.ids), None, ["contact", "linked"],
        )


def _benefit_fraud(
    data: Dataset, cfg: config.Config, customers: CustomerBase,
    agent: Agent, aid: str, day: datetime, trend: float,
) -> None:
    """(C) A refund or waiver for a customer who never paid anything."""
    if random.random() >= (cfg.benefit_fraud_per_month * trend) / 30:
        return
    target = random.choice([c for c in customers.ids if not data.purchase_history[c]] or customers.ids)
    ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
    contact_id = data.add_contact(ts, "agent_assisted", target, aid)
    data.add_access(ts, aid, target, contact_id, ["financial", "profile"])
    data.add_transaction(
        ts, target, random.choice(["refund", "fee_waiver"]),
        random.uniform(180, 2400), aid, contact_id, "agent_assisted",
    )


def _identity_takeover(
    data: Dataset, cfg: config.Config, customers: CustomerBase,
    agent: Agent, aid: str, day: datetime, trend: float,
) -> None:
    """(D) An agent rewrites most of a customer record, ID document included."""
    if random.random() >= (cfg.identity_fraud_per_month * trend) / 30:
        return
    target = random.choice(customers.ids)
    ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
    contact_id = data.add_contact(ts, "agent_assisted", target, aid)
    data.add_access(ts, aid, target, contact_id, ["identity", "contact", "profile"])
    fields = random.sample(
        ["residential_address", "mobile_phone", "email", "identity_document", "bank_account"],
        random.randint(4, 5),
    )
    data.add_profile_change(ts, target, fields, aid, contact_id, "agent_assisted")


def _collusion(
    data: Dataset,
    cfg: config.Config,
    customers: CustomerBase,
    workforce: Workforce,
    roster: list[Agent],
    day: datetime,
    trend: float,
) -> None:
    """(E) Paired agents pull the same customers on the same day, neither on a call."""
    on_roster = {a["agent_id"] for a in roster}
    for a1, a2 in workforce.collusion_pairs:
        if a1 not in on_roster or a2 not in on_roster:
            continue
        if random.random() < 0.04 * trend:
            shared = random.sample(customers.ids, random.randint(2, 4))
            base = helpers.stamp(day, cfg, shift=workforce.by_id[a1]["shift_pattern"])
            for cust in shared:
                data.add_access(base, a1, cust, None, ["contact", "linked"])
                data.add_access(
                    base + timedelta(minutes=random.randint(5, 180)), a2, cust, None,
                    ["contact", "linked"],
                )


def _external_takeover(
    data: Dataset, cfg: config.Config, customers: CustomerBase, day: datetime, trend: float
) -> None:
    """(F) Failed logins from an unfamiliar IP, a success, then a valuable change."""
    if random.random() >= (cfg.account_takeovers_per_month * trend) / 30:
        return
    victim = random.choice(customers.ids)
    ts = helpers.stamp(day, cfg, hour=random.choice([0, 1, 2, 3, 4, 22, 23]))
    attacker_ip = helpers.ip_address(residential=False)
    for k in range(random.randint(4, 9)):
        data.add_auth_event(ts - timedelta(minutes=12 - k), victim, "failed_login", attacker_ip, "Chrome/Linux")
    data.add_auth_event(ts, victim, "login_success", attacker_ip, "Chrome/Linux")
    contact_id = data.add_contact(ts, "self_service", victim)
    data.add_profile_change(
        ts + timedelta(minutes=random.randint(1, 20)), victim,
        ["mobile_phone", "email"], None, contact_id, "self_service",
    )
    data.add_transaction(
        ts + timedelta(minutes=random.randint(2, 40)), victim,
        random.choice(["renewal", "replacement_document"]),
        random.uniform(40, 300), None, contact_id, "self_service",
    )


def _post_termination_access(
    data: Dataset,
    cfg: config.Config,
    customers: CustomerBase,
    workforce: Workforce,
    date_range: list[datetime],
) -> None:
    """(G) A departed officer's credentials are still live.

    Runs once after the day loop, not inside it -- these accesses are dated
    relative to each leaver's termination, not to the day being generated.
    """
    for agent in workforce.agents:
        if agent["_termination_dt"] is None or not agent["_dishonest"]:
            continue
        for _ in range(random.randint(*cfg.post_termination_accesses)):
            day = agent["_termination_dt"] + timedelta(days=random.randint(2, 70))
            if day > date_range[-1]:
                continue
            data.add_access(
                helpers.stamp(day, cfg, hour=random.randint(19, 23)), agent["agent_id"],
                random.choice(customers.ids), None, ["contact", "linked"],
            )
