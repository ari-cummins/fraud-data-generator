"""Command-line entry point: `fraud-generate`.

Uses argparse rather than Typer deliberately. The CLI has eight flags and no
subcommands, which argparse covers with zero added dependencies -- worth more
to a package whose only runtime requirement is pandas than the nicer help
output would be.

This module is the one place in the package that configures logging or writes
to stdout. Library code logs and returns; the CLI decides where that goes.
"""

from __future__ import annotations

import argparse
import logging
import sys

from fraud_generator import __version__
from fraud_generator.config import Config, ConfigError
from fraud_generator.engine import generate
from fraud_generator.export import (
    LabelLeakError,
    build_tables,
    check_no_labels,
    format_summary,
    write_tables,
)

logger = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_LABEL_LEAK = 1
EXIT_BAD_CONFIG = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fraud-generate",
        description="Generate a synthetic contact-centre dataset with fraud planted in it.",
        epilog="Output is deterministic for a given --seed.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--seed", type=int, default=Config.seed,
                        help=f"RNG seed (default: {Config.seed})")
    parser.add_argument("-o", "--out", default=Config.output_dir, metavar="DIR",
                        help=f"output directory (default: {Config.output_dir})")

    size = parser.add_argument_group("dataset size")
    size.add_argument("--customers", type=int, default=Config.num_customers,
                      help=f"number of customers (default: {Config.num_customers})")
    size.add_argument("--agents", type=int, default=Config.num_agents,
                      help=f"number of agents (default: {Config.num_agents})")
    size.add_argument("--years", type=int, default=Config.years,
                      help=f"years of activity (default: {Config.years})")
    size.add_argument("--contacts-per-day", type=int, default=Config.contacts_per_day,
                      help=f"weekday contact volume (default: {Config.contacts_per_day})")

    out = parser.add_argument_group("output")
    out.add_argument("--no-write", action="store_true",
                     help="generate and summarise without writing CSVs")
    verbosity = out.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    verbosity.add_argument("-q", "--quiet", action="store_true", help="errors only")
    return parser


def _configure_logging(verbose: bool, quiet: bool) -> None:
    level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)-7s %(name)s: %(message)s", stream=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose, args.quiet)

    try:
        cfg = Config(
            seed=args.seed,
            output_dir=args.out,
            num_customers=args.customers,
            num_agents=args.agents,
            years=args.years,
            contacts_per_day=args.contacts_per_day,
        )
    except ConfigError as exc:
        print(f"fraud-generate: {exc}", file=sys.stderr)
        return EXIT_BAD_CONFIG

    data, workforce, customers = generate(cfg)
    tables = build_tables(data, workforce, customers)

    try:
        check_no_labels(tables)
    except LabelLeakError as exc:
        # Never write a dataset that failed the guard rail: a labelled export is
        # worse than no export, because it looks usable.
        print(f"fraud-generate: refusing to write - {exc}", file=sys.stderr)
        return EXIT_LABEL_LEAK

    if not args.no_write:
        write_tables(tables, cfg.output_dir)

    print(format_summary(tables, cfg))
    if not args.no_write:
        print(f"\n  Written to {cfg.output_dir}/")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
