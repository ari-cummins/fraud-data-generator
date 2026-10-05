"""Agents and customers.

Agents carry two hidden fields, `_dishonest` and `_termination_dt`, prefixed
with underscores and stripped before export. Seniority is a mild risk factor
for offending, since broader access enables more; at least two offenders also
leave part-way through the window, which guarantees the post-termination
pattern exists to be found.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from fraud_generator import config, helpers, pools

Agent = dict[str, object]
Customer = dict[str, object]


@dataclass
class Workforce:
    """The agent population, plus the lookups the engine needs over it."""

    agents: list[Agent]
    dishonest_ids: list[str]
    collusion_pairs: list[tuple[str, str]]
    by_id: dict[str, Agent]

    def active_on(self, day: datetime) -> list[Agent]:
        """Agents employed on this date. Used for legitimate rostering only."""
        return [a for a in self.agents
                if a["_termination_dt"] is None or a["_termination_dt"] > day]


@dataclass
class CustomerBase:
    """The customer population, plus the id lists the engine samples from."""

    customers: list[Customer]
    ids: list[str]
    protected_ids: list[str]


def build_workforce(cfg: config.Config) -> Workforce:
    agents: list[Agent] = []
    for i in range(cfg.num_agents):
        hire = cfg.start_date - timedelta(days=random.randint(30, 365 * 9))
        shift = random.choices(["day", "evening", "night"], weights=[0.62, 0.28, 0.10])[0]
        leaves = random.random() < cfg.p_agent_terminated
        termination = None
        if leaves:
            # Terminate part-way through the window so post-departure activity is visible.
            termination = cfg.start_date + timedelta(days=random.randint(120, cfg.total_days - 60))

        agents.append({
            "agent_id": helpers.seq_id("AGT", i + 1),
            "full_name": helpers.full_name(),
            "team": random.choice(pools.TEAMS),
            "role": random.choices(pools.ROLES, weights=[0.62, 0.23, 0.10, 0.05])[0],
            "access_level": random.choices(pools.ACCESS_LEVELS, weights=[0.72, 0.21, 0.07])[0],
            "shift_pattern": shift,
            "site": random.choice(pools.SITES),
            "hire_date": hire.date().isoformat(),
            "termination_date": termination.date().isoformat() if termination else None,
            # --- hidden, dropped before export ---
            "_dishonest": False,
            "_termination_dt": termination,
        })

    # Assign the hidden propensity. Seniority is a mild risk factor (broader access).
    #
    # Floor of 4, not 3: the collusion block below needs four offenders to form
    # two pairs. A floor of 3 made that guard unsatisfiable at any config where
    # num_agents * p_agent_dishonest < 4, which silently produced datasets with
    # no collusion in them at all.
    n_bad = max(4, int(cfg.num_agents * cfg.p_agent_dishonest))
    weights = [3 if a["access_level"] in ("senior", "admin") else 1 for a in agents]
    dishonest: set[int] = set()
    while len(dishonest) < n_bad:
        dishonest.add(random.choices(range(cfg.num_agents), weights=weights)[0])
    for i in dishonest:
        agents[i]["_dishonest"] = True

    # Make sure at least two offenders also leave part-way through the window, so
    # the post-termination pattern exists to be found.
    leavers = [i for i in dishonest if agents[i]["_termination_dt"] is not None]
    for i in list(dishonest)[:max(0, 2 - len(leavers))]:
        t = cfg.start_date + timedelta(days=random.randint(150, cfg.total_days - 90))
        agents[i]["_termination_dt"] = t
        agents[i]["termination_date"] = t.date().isoformat()

    # Two pairs of dishonest agents work together -- this is what makes the
    # collusion rule findable. They share an unusual number of no-contact lookups.
    bad_ids = [agents[i]["agent_id"] for i in sorted(dishonest)]
    collusion_pairs: list[tuple[str, str]] = []
    if len(bad_ids) >= 4:
        shuffled = bad_ids[:]
        random.shuffle(shuffled)
        collusion_pairs = [(shuffled[0], shuffled[1]), (shuffled[2], shuffled[3])]

    agent_by_id = {a["agent_id"]: a for a in agents}

    return Workforce(agents, bad_ids, collusion_pairs, agent_by_id)


def build_customers(cfg: config.Config) -> CustomerBase:
    customers: list[Customer] = []
    for i in range(cfg.num_customers):
        line, suburb, state, postcode = helpers.street_address()
        customers.append({
            "customer_id": helpers.seq_id("CUS", i + 1),
            "full_name": helpers.full_name(),
            "date_of_birth": helpers.date_of_birth(cfg),
            "residential_address": line,
            "suburb": suburb,
            "state": state,
            "postcode": postcode,
            "mobile_phone": helpers.mobile_number(),
            "email": f"{random.choice(pools.FIRST_NAMES).lower()}.{random.choice(pools.LAST_NAMES).lower().replace(chr(39),'')}{random.randint(1,999)}@example.com",
            "customer_since": (cfg.start_date - timedelta(days=random.randint(200, 365 * 12))).date().isoformat(),
            # A real business attribute: court order or safety concern. Not a
            # fraud flag -- but Rule 1 weights lookups against these customers.
            "protected_person": random.random() < 0.012,
            "linked_customer_id": None,
        })

    # ~5% of customers share a household or joint registration.
    for c in random.sample(customers, int(cfg.num_customers * 0.05)):
        other = random.choice(customers)
        if other["customer_id"] != c["customer_id"]:
            c["linked_customer_id"] = other["customer_id"]

    customer_ids = [c["customer_id"] for c in customers]
    protected_ids = [c["customer_id"] for c in customers if c["protected_person"]]

    return CustomerBase(customers, customer_ids, protected_ids)
