"""Dataset: the row builders and the state they share."""

from datetime import datetime

from fraud_generator.builders import Dataset

TS = datetime(2023, 1, 1, 10, 0, 0)


def test_two_datasets_have_independent_id_sequences():
    a, b = Dataset(), Dataset()
    assert a.add_contact(TS, "self_service", "CUS-00000001") == "CON-00000001"
    assert a.add_contact(TS, "self_service", "CUS-00000002") == "CON-00000002"
    assert b.add_contact(TS, "self_service", "CUS-00000003") == "CON-00000001"
    assert len(a.contacts) == 2
    assert len(b.contacts) == 1


def test_id_prefixes_are_per_table():
    d = Dataset()
    cid = d.add_contact(TS, "agent_assisted", "CUS-00000001", "AGT-00000001")
    aid = d.add_access(TS, "AGT-00000001", "CUS-00000001", cid, ["profile"])
    tid = d.add_transaction(TS, "CUS-00000001", "purchase", 10.0, "AGT-00000001", cid, "agent_assisted")
    assert cid.startswith("CON-") and aid.startswith("ACC-") and tid.startswith("TXN-")


def test_profile_change_writes_one_row_per_field():
    d = Dataset()
    d.add_profile_change(TS, "CUS-00000001", ["email", "mobile_phone", "identity_document"],
                         "AGT-00000001", "CON-00000001", "agent_assisted")
    assert len(d.profile_changes) == 3
    assert {r["field_changed"] for r in d.profile_changes} == {
        "email", "mobile_phone", "identity_document"
    }


def test_purchase_history_records_only_purchases_and_renewals():
    d = Dataset()
    for txn_type in ("purchase", "renewal", "refund", "fee_waiver"):
        d.add_transaction(TS, "CUS-00000001", txn_type, 50.0, None, None, "self_service")
    assert len(d.purchase_history["CUS-00000001"]) == 2


def test_access_accepts_a_null_contact_id():
    d = Dataset()
    d.add_access(TS, "AGT-00000001", "CUS-00000001", None, ["profile"])
    assert d.crm_access[0]["contact_id"] is None


def test_no_builder_writes_a_label_field():
    d = Dataset()
    cid = d.add_contact(TS, "agent_assisted", "CUS-00000001", "AGT-00000001")
    d.add_access(TS, "AGT-00000001", "CUS-00000001", cid, ["profile"])
    d.add_transaction(TS, "CUS-00000001", "refund", 10.0, "AGT-00000001", cid, "agent_assisted")
    d.add_profile_change(TS, "CUS-00000001", ["email"], "AGT-00000001", cid, "agent_assisted")
    d.add_auth_event(TS, "CUS-00000001", "failed_login")

    banned = ("fraud", "label", "scenario", "suspicious", "risk")
    for table in (d.contacts, d.crm_access, d.transactions, d.profile_changes, d.auth_events):
        for row in table:
            for key in row:
                assert not any(b in key.lower() for b in banned)
