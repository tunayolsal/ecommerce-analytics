"""
run_pipeline.py — orchestrates the full extract -> transform -> load flow
for the Olist analytics warehouse, then runs basic data-quality checks
against the loaded DuckDB database.

Usage:
    python -m etl.run_pipeline
    (or)  python etl/run_pipeline.py

If data/raw/ doesn't contain the Kaggle CSVs yet, this exits with a clear,
actionable message instead of a stack trace.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow running as a plain script (python etl/run_pipeline.py) as well as a
# module (python -m etl.run_pipeline) by ensuring the project root is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.extract import extract_all  # noqa: E402
from etl.load import DB_PATH, load_all  # noqa: E402
from etl.transform import transform_all  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Data-quality checks
# ----------------------------------------------------------------------------

# (table, primary/natural-key columns) — used for duplicate-key checks.
# geolocation is intentionally excluded: it has no natural key (see schema.sql).
_KEY_CHECKS = {
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "product_category_translation": ["product_category_name"],
}

_DATE_RANGE_CHECKS = {
    "orders": "order_purchase_timestamp",
    "order_reviews": "review_creation_date",
}


def run_data_quality_checks(con) -> None:
    """Print row counts, null %, duplicate-key counts, and date ranges per table."""
    logger.info("=" * 70)
    logger.info("DATA QUALITY REPORT")
    logger.info("=" * 70)

    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]

    for table in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info("- %-30s %8d rows", table, count)

        # Null percentage per column.
        columns = [row[1] for row in con.execute(f"PRAGMA table_info('{table}')").fetchall()]
        if count > 0:
            null_exprs = ", ".join(
                f"ROUND(100.0 * SUM(CASE WHEN {c} IS NULL THEN 1 ELSE 0 END) / {count}, 1) AS {c}"
                for c in columns
            )
            null_pcts = con.execute(f"SELECT {null_exprs} FROM {table}").fetchone()
            notable_nulls = {c: p for c, p in zip(columns, null_pcts) if p and p > 0}
            if notable_nulls:
                nulls_str = ", ".join(f"{c}={p}%" for c, p in notable_nulls.items())
                logger.info("    null%%: %s", nulls_str)

        # Duplicate natural-key check.
        if table in _KEY_CHECKS and count > 0:
            key_cols = ", ".join(_KEY_CHECKS[table])
            dup_count = con.execute(
                f"""
                SELECT COUNT(*) FROM (
                    SELECT {key_cols}, COUNT(*) AS n
                    FROM {table}
                    GROUP BY {key_cols}
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
            if dup_count:
                logger.warning("    duplicate key groups on (%s): %d", key_cols, dup_count)
            else:
                logger.info("    key (%s): no duplicates", key_cols)

        # Date range check.
        if table in _DATE_RANGE_CHECKS and count > 0:
            col = _DATE_RANGE_CHECKS[table]
            min_d, max_d = con.execute(f"SELECT MIN({col}), MAX({col}) FROM {table}").fetchone()
            logger.info("    %s range: %s -> %s", col, min_d, max_d)

    # Referential sanity: orders whose customer_id has no match in customers.
    orphan_orders = con.execute(
        """
        SELECT COUNT(*) FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
        """
    ).fetchone()[0]
    if orphan_orders:
        logger.warning("Referential check: %d orders reference a missing customer_id", orphan_orders)
    else:
        logger.info("Referential check: all orders.customer_id resolve to a customer")

    logger.info("=" * 70)


def main() -> int:
    logger.info("Starting Olist ETL pipeline")

    try:
        logger.info("Step 1/3: extract")
        raw = extract_all()
    except FileNotFoundError as exc:
        logger.error("Cannot run pipeline — raw data not found.\n%s", exc)
        return 1

    logger.info("Step 2/3: transform")
    cleaned = transform_all(raw)

    logger.info("Step 3/3: load")
    con = load_all(cleaned)

    run_data_quality_checks(con)
    con.close()

    logger.info("Pipeline complete. Database written to %s", DB_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
