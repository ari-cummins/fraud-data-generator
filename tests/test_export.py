"""Export: table shaping, the label guard rail, and writing."""

import os

import pandas as pd
import pytest

from fraud_generator.export import (
    LabelLeakError,
    build_tables,
    check_no_labels,
    format_summary,
    write_tables,
)

TABLE_NAMES = {
    "agents", "customers", "contacts", "crm_access",
    "transactions", "profile_changes", "auth_events",
}


@pytest.fixture(scope="session")
def tables(small_dataset):
    data, workforce, customers, _ = small_dataset
    return build_tables(data, workforce, customers)


def test_build_tables_returns_all_seven(tables):
    assert set(tables) == TABLE_NAMES


def test_hidden_agent_columns_are_dropped(tables):
    assert "_dishonest" not in tables["agents"].columns
    assert "_termination_dt" not in tables["agents"].columns


def test_real_tables_pass_the_guard_rail(tables):
    check_no_labels(tables)


@pytest.mark.parametrize(
    "bad_column",
    ["fraud_score", "is_fraud", "scenario_type", "risk_score", "label", "anomaly", "is_bad"],
)
def test_guard_rail_rejects_label_columns(bad_column):
    tables = {"contacts": pd.DataFrame({"contact_id": ["CON-1"], bad_column: [1]})}
    with pytest.raises(LabelLeakError, match=bad_column):
        check_no_labels(tables)


@pytest.mark.parametrize("position", ["first", "middle", "last"])
def test_guard_rail_rejects_internal_columns_in_any_position(position):
    """The original guard only checked the last column of each table.

    An internal column anywhere else sailed through, which is why this is
    parametrised by position rather than just asserting one case.
    """
    cols = {"a": [1], "b": [2], "c": [3]}
    order = {
        "first": ["_hidden", "a", "b"],
        "middle": ["a", "_hidden", "b"],
        "last": ["a", "b", "_hidden"],
    }[position]
    cols["_hidden"] = [9]
    df = pd.DataFrame(cols)[order]
    with pytest.raises(LabelLeakError, match="_hidden"):
        check_no_labels({"contacts": df})


def test_write_tables_writes_one_csv_per_table(tables, tmp_path):
    written = write_tables(tables, str(tmp_path))
    assert len(written) == len(TABLE_NAMES)
    for name in TABLE_NAMES:
        path = tmp_path / f"{name}.csv"
        assert path.exists() and path.stat().st_size > 0


def test_written_csv_round_trips(tables, tmp_path):
    write_tables(tables, str(tmp_path))
    reloaded = pd.read_csv(tmp_path / "contacts.csv")
    assert len(reloaded) == len(tables["contacts"])
    assert list(reloaded.columns) == list(tables["contacts"].columns)


def test_write_tables_creates_a_missing_directory(tables, tmp_path):
    target = tmp_path / "does" / "not" / "exist"
    write_tables(tables, str(target))
    assert os.path.isdir(target)


def test_format_summary_mentions_every_table(tables, small_cfg):
    summary = format_summary(tables, small_cfg)
    for name in TABLE_NAMES:
        assert name in summary
    assert "no fraud labels present" in summary
