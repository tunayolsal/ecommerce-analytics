"""
export_marts.py — run each SQL file in sql/analysis/ against
data/olist.duckdb and export every result set to a small parquet "mart" in
data/processed/, for the Streamlit dashboard (M4) to read directly without
needing a live DuckDB connection.

Each analysis .sql file may contain multiple queries, separated by a marker
comment of the form:

    -- @name: some_result_name

Everything between one marker and the next (or end of file) is treated as a
single SQL statement and exported to data/processed/<name>.parquet.

Usage:
    python etl/export_marts.py
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "olist.duckdb"
ANALYSIS_DIR = ROOT / "sql" / "analysis"
OUTPUT_DIR = ROOT / "data" / "processed"

NAME_MARKER = re.compile(r"^--\s*@name:\s*(\w+)\s*$", re.MULTILINE)


def split_queries(sql_text: str) -> list[tuple[str, str]]:
    """Split a SQL file into (name, statement) pairs based on @name markers."""
    matches = list(NAME_MARKER.finditer(sql_text))
    if not matches:
        raise ValueError("No '-- @name: ...' markers found in SQL file")

    queries = []
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(sql_text)
        statement = sql_text[start:end].strip()
        # strip trailing semicolon(s) — duckdb handles it fine either way,
        # but keep it clean
        statement = statement.rstrip(";").strip()
        if statement:
            queries.append((name, statement))
    return queries


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run M1 pipeline first.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    sql_files = sorted(ANALYSIS_DIR.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"No .sql files found in {ANALYSIS_DIR}")

    logger.info("Found %d analysis SQL files", len(sql_files))

    total_exported = 0
    for sql_file in sql_files:
        logger.info("=== %s ===", sql_file.name)
        sql_text = sql_file.read_text(encoding="utf-8")
        queries = split_queries(sql_text)

        for name, statement in queries:
            out_path = OUTPUT_DIR / f"{name}.parquet"
            try:
                result_df = con.execute(statement).fetchdf()
            except Exception as exc:
                logger.error("FAILED query '%s' in %s: %s", name, sql_file.name, exc)
                raise

            result_df.to_parquet(out_path, index=False)
            total_exported += 1

            logger.info(
                "  -> %s: %d rows, %d cols -> %s",
                name,
                len(result_df),
                len(result_df.columns),
                out_path.relative_to(ROOT),
            )
            logger.info("     head:\n%s", result_df.head(3).to_string(index=False))

    con.close()
    logger.info("Done. Exported %d parquet marts to %s", total_exported, OUTPUT_DIR)


if __name__ == "__main__":
    main()
