"""The command-line entry point."""

import pytest

from fraud_generator.cli import EXIT_BAD_CONFIG, EXIT_OK, build_parser, main

TINY = ["--customers", "40", "--agents", "4", "--years", "1", "--contacts-per-day", "5"]


def test_parser_defaults_match_the_config_defaults():
    from fraud_generator.config import Config

    args = build_parser().parse_args([])
    assert args.seed == Config.seed
    assert args.customers == Config.num_customers
    assert args.agents == Config.num_agents
    assert args.years == Config.years


def test_generates_and_writes(tmp_path, capsys):
    code = main(TINY + ["--out", str(tmp_path), "--quiet"])
    assert code == EXIT_OK
    assert (tmp_path / "contacts.csv").exists()
    assert "Written to" in capsys.readouterr().out


def test_no_write_skips_the_csvs(tmp_path, capsys):
    code = main(TINY + ["--out", str(tmp_path), "--no-write", "--quiet"])
    assert code == EXIT_OK
    assert not (tmp_path / "contacts.csv").exists()
    out = capsys.readouterr().out
    assert "no fraud labels present" in out
    assert "Written to" not in out


def test_bad_config_exits_two_without_a_traceback(tmp_path, capsys):
    code = main(["--customers", "0", "--out", str(tmp_path), "--quiet"])
    assert code == EXIT_BAD_CONFIG
    assert "num_customers" in capsys.readouterr().err


def test_same_seed_produces_identical_output(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    main(TINY + ["--out", str(a), "--seed", "7", "--quiet"])
    main(TINY + ["--out", str(b), "--seed", "7", "--quiet"])
    assert (a / "contacts.csv").read_bytes() == (b / "contacts.csv").read_bytes()


def test_different_seeds_produce_different_output(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    main(TINY + ["--out", str(a), "--seed", "7", "--quiet"])
    main(TINY + ["--out", str(b), "--seed", "8", "--quiet"])
    assert (a / "contacts.csv").read_bytes() != (b / "contacts.csv").read_bytes()


def test_version_flag_exits_cleanly():
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
