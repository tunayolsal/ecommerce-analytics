"""
load.py — (re)create the DuckDB database from sql/schema.sql and load the
cleaned DataFrames produced by transform.py into their target tables.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "olist.duckdb"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

# Order matters only for readability here — DuckDB does not enforce FK
# constraints at insert time, so tables can be loaded in any order. We still
# load "reference" tables first for clarity.
TABLE_LOAD_ORDER = [
    "product_category_translation",
    "customers",
    "sellers",
    "geolocation",
    "products",
    "orders",
    "order_items",
    "order_payments",
    "order_reviews",
]


def create_schema(con: duckdb.DuckDBPyConnection, schema_path: Path = SCHEMA_PATH) -> None:
    """Execute sql/schema.sql against the given DuckDB connection."""
    sql = schema_path.read_text(encoding="utf-8")
    con.execute(sql)
    logger.info("Schema created from %s", schema_path)


def load_all(cleaned: dict[str, pd.DataFrame], db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    """
    Create a fresh DuckDB database at db_path (overwriting any existing file),
    build the schema, and load every cleaned table via DuckDB's zero-copy
    pandas integration. Returns the open connection for downstream use
    (e.g. data-quality checks in run_pipeline.py).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        db_path.unlink()
        logger.info("Removed existing database at %s", db_path)

    con = duckdb.connect(str(db_path))
    create_schema(con)

    for table_name in TABLE_LOAD_ORDER:
        df = cleaned[table_name]
        con.register("tmp_df", df)
        con.execute(f"INSERT INTO {table_name} SELECT * FROM tmp_df")
        con.unregister("tmp_df")
        logger.info("Loaded %-30s %6d rows into '%s'", table_name, len(df), table_name)

    con.commit()
    logger.info("Database ready at %s", db_path)
    return con
