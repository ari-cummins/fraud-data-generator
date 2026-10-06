"""Synthetic contact-centre fraud data generator.

Generates seven relational tables of contact-centre activity for an Australian
government service agency. The design constraint: there are no fraud flags
anywhere in the output. Every row is an ordinary business record, and fraud
exists only as a pattern across rows.

    from fraud_generator import Config, generate, build_tables, write_tables

    data, workforce, customers = generate(Config(seed=42))
    tables = build_tables(data, workforce, customers)
    write_tables(tables, "output")
"""

from fraud_generator.config import DEFAULT, Config, ConfigError
from fraud_generator.engine import GenerationResult, generate
from fraud_generator.export import (
    LabelLeakError,
    build_tables,
    check_no_labels,
    format_summary,
    write_tables,
)

__version__ = "0.2.0"

__all__ = [
    "Config",
    "ConfigError",
    "DEFAULT",
    "GenerationResult",
    "LabelLeakError",
    "__version__",
    "build_tables",
    "check_no_labels",
    "format_summary",
    "generate",
    "write_tables",
]
