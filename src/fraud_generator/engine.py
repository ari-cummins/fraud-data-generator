import random
from datetime import timedelta

from fraud_generator import config, helpers, pools
from fraud_generator.actors import build_customers, build_workforce
from fraud_generator.builders import Dataset


def generate(cfg=None):
    """Generate one complete dataset. Returns (data, workforce, customers)."""
    cfg = config.DEFAULT if cfg is None else cfg
    random.seed(cfg.seed)

    date_range = cfg.date_range

    workforce = build_workforce(cfg)
    customers = build_customers(cfg)
    data = Dataset()

    for day_index, day in enumerate(date_range):
        weekday = day.weekday() < 5
        volume = int(cfg.contacts_per_day * (1.0 if weekday else 0.35))
        roster = workforce.active_on(day)
        if not roster:
            continue
        trend = helpers.year_weight(day_index, cfg)

        # ---------------------------------------------------------------- ordinary
        for _ in range(volume):
            customer_id = random.choice(customers.ids)
            agent_assisted = random.random() > cfg.p_self_service

            if agent_assisted:
                agent = random.choice(roster)
                ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
                contact_id = data.add_contact(ts, "agent_assisted", customer_id, agent["agent_id"])

                # the lookups that go with the call — pretext satisfied. An agent
                # typically opens two or three screens while handling one contact.
                for k in range(random.randint(1, 3)):
                    data.add_access(ts + timedelta(seconds=random.randint(0, 600)),
                            agent["agent_id"], customer_id, contact_id,
                            random.sample(list(pools.FIELD_GROUPS), k=random.randint(1, 3)))

                # legitimate warm transfer: agent opens a second customer's record
                if random.random() < cfg.p_legit_warm_transfer:
                    data.add_access(ts + timedelta(minutes=random.randint(1, 6)), agent["agent_id"],
                            random.choice(customers.ids), contact_id, ["profile", "contact"])

                if random.random() < cfg.p_contact_has_transaction:
                    if random.random() < cfg.p_txn_is_refund:
                        # honest refunds overwhelmingly follow a real purchase
                        if data.purchase_history[customer_id] and random.random() < cfg.p_legit_refund_has_purchase:
                            data.add_transaction(ts, customer_id, random.choice(["refund", "fee_waiver"]),
                                            random.uniform(25, 320), agent["agent_id"], contact_id, "agent_assisted")
                    else:
                        data.add_transaction(ts, customer_id, random.choice(["purchase", "renewal"]),
                                        random.uniform(20, 450), agent["agent_id"], contact_id, "agent_assisted")

                if random.random() < cfg.p_contact_has_profile_change:
                    # honest updates touch one field, or two when someone moves house
                    if random.random() < cfg.p_legit_3_field_change:
                        # an honest bulk update is a change of circumstances: new
                        # address, new phone, new email. It never rewrites the
                        # identity document or bank account in the same breath.
                        fields = random.sample(
                            ["residential_address", "postal_address", "mobile_phone",
                            "email", "preferred_name"], 3)
                    elif random.random() < 0.30:
                        fields = ["residential_address", "postal_address"]
                    else:
                        fields = [random.choice(pools.PROFILE_FIELDS)]
                    data.add_profile_change(ts, customer_id, fields, agent["agent_id"], contact_id, "agent_assisted")

            else:
                ts = helpers.stamp(day, cfg, hour=random.randint(6, 23))
                ip = helpers.ip_address()
                ua = random.choice(pools.USER_AGENTS)

                # honest people mistype their password all the time
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
                        data.add_transaction(ts, customer_id, "refund", random.uniform(25, 200), None, contact_id, "self_service")
                    else:
                        data.add_transaction(ts, customer_id, random.choice(["purchase", "renewal"]),
                                        random.uniform(20, 450), None, contact_id, "self_service")

                if random.random() < cfg.p_contact_has_profile_change * 0.5:
                    data.add_profile_change(ts, customer_id, [random.choice(pools.PROFILE_FIELDS)], None, contact_id, "self_service")

        # legitimate lookups with no call attached — QA sampling, callback prep,
        # complaint handling. These are why "no contact_id" is not itself damning.
        for _ in range(int(volume * cfg.p_legit_no_contact_access)):
            agent = random.choice(roster)
            data.add_access(helpers.stamp(day, cfg, shift=agent["shift_pattern"]), agent["agent_id"],
                    random.choice(customers.ids), None, ["profile"])

        # ------------------------------------------------------- driven by propensity
        for agent in roster:
            if not agent["_dishonest"]:
                continue
            aid = agent["agent_id"]

            # (A) Unlawful locate — looking up people with no business reason.
            #     Some during rostered hours, some late at night.
            if random.random() < (cfg.locate_lookups_per_month* trend) / 30:
                target = random.choice(customers.protected_ids) if (customers.protected_ids and random.random() < 0.35) \
                    else random.choice(customers.ids)
                if random.random() < cfg.p_locate_after_hours:
                    hours = [h for h in range(24) if not helpers.in_shift(h, agent["shift_pattern"], cfg)]
                    ts = helpers.stamp(day, cfg, hour=random.choice(hours))
                else:
                    ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
                data.add_access(ts, aid, target, None, ["contact", "linked", "profile"])

            # (B) Excessive lookups — a burst of unrelated records in one hour.
            if random.random() < (cfg.velocity_bursts_per_year * trend) / 365:
                base = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
                for _ in range(random.randint(*cfg.velocity_burst_size)):
                    data.add_access(base + timedelta(minutes=random.randint(0, 55)), aid,
                            random.choice(customers.ids), None, ["contact", "linked"])

            # (C) Benefit fraud — a refund or waiver processed for a customer who
            #     never paid anything. Built by the same transaction function.
            if random.random() < (cfg.benefit_fraud_per_month * trend) / 30:
                target = random.choice([c for c in customers.ids if not data.purchase_history[c]] or customers.ids)
                ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
                contact_id = data.add_contact(ts, "agent_assisted", target, aid)
                data.add_access(ts, aid, target, contact_id, ["financial", "profile"])
                data.add_transaction(ts, target, random.choice(["refund", "fee_waiver"]),
                                random.uniform(180, 2400), aid, contact_id, "agent_assisted")

            # (D) Identity takeover at the counter — an agent rewrites most of a
            #     customer record in a single contact, including the ID document.
            if random.random() < (cfg.identity_fraud_per_month * trend) / 30:
                target = random.choice(customers.ids)
                ts = helpers.stamp(day, cfg, shift=agent["shift_pattern"])
                contact_id = data.add_contact(ts, "agent_assisted", target, aid)
                data.add_access(ts, aid, target, contact_id, ["identity", "contact", "profile"])
                fields = random.sample(["residential_address", "mobile_phone", "email",
                                        "identity_document", "bank_account"], random.randint(4, 5))
                data.add_profile_change(ts, target, fields, aid, contact_id, "agent_assisted")

        # (E) Collusion — paired agents pull the same customers on the same day,
        #     neither of them on a call. Emerges as an abnormal shared-customer count.
        for a1, a2 in workforce.collusion_pairs:
            if a1 not in {a["agent_id"] for a in roster} or a2 not in {a["agent_id"] for a in roster}:
                continue
            if random.random() < 0.04 * trend:
                shared = random.sample(customers.ids, random.randint(2, 4))
                base = helpers.stamp(day, cfg, shift=workforce.by_id[a1]["shift_pattern"])
                for cust in shared:
                    data.add_access(base, a1, cust, None, ["contact", "linked"])
                    data.add_access(base + timedelta(minutes=random.randint(5, 180)), a2, cust, None, ["contact", "linked"])

        # (F) External account takeover — a run of failed logins from an unfamiliar
        #     IP, then a success, then a valuable change. Same builders as above.
        if random.random() < (cfg.account_takeovers_per_month * trend) / 30:
            victim = random.choice(customers.ids)
            ts = helpers.stamp(day, cfg, hour=random.choice([0, 1, 2, 3, 4, 22, 23]))
            attacker_ip = helpers.ip_address(residential=False)
            for k in range(random.randint(4, 9)):
                data.add_auth_event(ts - timedelta(minutes=12 - k), victim, "failed_login", attacker_ip, "Chrome/Linux")
            data.add_auth_event(ts, victim, "login_success", attacker_ip, "Chrome/Linux")
            contact_id = data.add_contact(ts, "self_service", victim)
            data.add_profile_change(ts + timedelta(minutes=random.randint(1, 20)), victim,
                            ["mobile_phone", "email"], None, contact_id, "self_service")
            data.add_transaction(ts + timedelta(minutes=random.randint(2, 40)), victim,
                            random.choice(["renewal", "replacement_document"]),
                            random.uniform(40, 300), None, contact_id, "self_service")

    # (G) Post-termination access — a departed officer's credentials are still live.
    for agent in workforce.agents:
        if agent["_termination_dt"] is None or not agent["_dishonest"]:
            continue
        for _ in range(random.randint(*cfg.post_termination_accesses)):
            day = agent["_termination_dt"] + timedelta(days=random.randint(2, 70))
            if day > date_range[-1]:
                continue
            data.add_access(helpers.stamp(day, cfg, hour=random.randint(19, 23)), agent["agent_id"],
                    random.choice(customers.ids), None, ["contact", "linked"])

    return data, workforce, customers