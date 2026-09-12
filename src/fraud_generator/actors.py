import random
from dataclasses import dataclass
from datetime import timedelta

from fraud_generator import config, helpers, pools


@dataclass
class Workforce:
    agents: list
    dishonest_ids: list
    collusion_pairs: list
    by_id: dict

    def active_on(self, day):
        """Agents employed on this date. Used for legitimate rostering only."""
        return [a for a in self.agents
                if a["_termination_dt"] is None or a["_termination_dt"] > day]


@dataclass
class CustomerBase:
    customers: list
    ids: list
    protected_ids: list


def build_workforce():
    agents = []
    for i in range(config.NUM_AGENTS):
        hire = config.START_DATE - timedelta(days=random.randint(30, 365 * 9))
        shift = random.choices(["day", "evening", "night"], weights=[0.62, 0.28, 0.10])[0]
        leaves = random.random() < config.P_AGENT_TERMINATED
        termination = None
        if leaves:
            # terminate part-way through the window so post-departure activity is visible
            termination = config.START_DATE + timedelta(days=random.randint(120, config.TOTAL_DAYS - 60))

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
    n_bad = max(3, int(config.NUM_AGENTS * config.P_AGENT_DISHONEST))
    weights = [3 if a["access_level"] in ("senior", "admin") else 1 for a in agents]
    dishonest = set()
    while len(dishonest) < n_bad:
        dishonest.add(random.choices(range(config.NUM_AGENTS), weights=weights)[0])
    for i in dishonest:
        agents[i]["_dishonest"] = True

    # Make sure at least two offenders also leave part-way through the window, so
    # the post-termination pattern exists to be found.
    leavers = [i for i in dishonest if agents[i]["_termination_dt"] is not None]
    for i in list(dishonest)[:max(0, 2 - len(leavers))]:
        t = config.START_DATE + timedelta(days=random.randint(150, config.TOTAL_DAYS - 90))
        agents[i]["_termination_dt"] = t
        agents[i]["termination_date"] = t.date().isoformat()

    # Two pairs of dishonest agents work together — this is what makes the collusion
    # rule findable. They will share an unusual number of no-contact lookups.
    bad_ids = [agents[i]["agent_id"] for i in sorted(dishonest)]
    collusion_pairs = []
    if len(bad_ids) >= 4:
        shuffled = bad_ids[:]
        random.shuffle(shuffled)
        collusion_pairs = [(shuffled[0], shuffled[1]), (shuffled[2], shuffled[3])]

    agent_by_id = {a["agent_id"]: a for a in agents}

    return Workforce(agents, bad_ids, collusion_pairs, agent_by_id)


def build_customers():
    customers = []
    for i in range(config.NUM_CUSTOMERS):
        line, suburb, state, postcode = helpers.street_address()
        customers.append({
            "customer_id": helpers.seq_id("CUS", i + 1),
            "full_name": helpers.full_name(),
            "date_of_birth": helpers.date_of_birth(),
            "residential_address": line,
            "suburb": suburb,
            "state": state,
            "postcode": postcode,
            "mobile_phone": helpers.mobile_number(),
            "email": f"{random.choice(pools.FIRST_NAMES).lower()}.{random.choice(pools.LAST_NAMES).lower().replace(chr(39),'')}{random.randint(1,999)}@example.com",
            "customer_since": (config.START_DATE - timedelta(days=random.randint(200, 365 * 12))).date().isoformat(),
            "protected_person": random.random() < 0.012,  # court order / safety concern — a real business attribute
            "linked_customer_id": None,
        })

    # ~5% of customers share a household or joint registration
    for c in random.sample(customers, int(config.NUM_CUSTOMERS * 0.05)):
        other = random.choice(customers)
        if other["customer_id"] != c["customer_id"]:
            c["linked_customer_id"] = other["customer_id"]

    customer_ids = [c["customer_id"] for c in customers]
    protected_ids = [c["customer_id"] for c in customers if c["protected_person"]]

    return CustomerBase(customers, customer_ids, protected_ids)