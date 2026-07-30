"""
extract.py — read the raw Olist Kaggle CSVs from data/raw/ into pandas
DataFrames with explicit, correct dtypes and parsed dates.

The Kaggle download ("Brazilian E-Commerce Public Dataset by Olist") ships
9 CSVs. This module knows the exact column layout of each and loads them
defensively: missing files raise a clear FileNotFoundError that the pipeline
runner turns into a friendly message, rather than a cryptic pandas traceback.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Directory containing the raw Kaggle CSVs (not committed to git — see .gitignore).
RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Filenames as distributed by Kaggle.
RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "product_category_translation": "product_category_name_translation.csv",
}

# Columns that should be parsed as timestamps per table.
_DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}

# Dtypes to force at read time (IDs and zip codes must stay strings — they
# contain leading zeros / are never used arithmetically).
_DTYPES = {
    "orders": {
        "order_id": "string",
        "customer_id": "string",
        "order_status": "string",
    },
    "customers": {
        "customer_id": "string",
        "customer_unique_id": "string",
        "customer_zip_code_prefix": "string",
        "customer_city": "string",
        "customer_state": "string",
    },
    "order_items": {
        "order_id": "string",
        "order_item_id": "int64",
        "product_id": "string",
        "seller_id": "string",
        "price": "float64",
        "freight_value": "float64",
    },
    "products": {
        "product_id": "string",
        "product_category_name": "string",
        "product_name_lenght": "Float64",
        "product_description_lenght": "Float64",
        "product_photos_qty": "Float64",
        "product_weight_g": "float64",
        "product_length_cm": "float64",
        "product_height_cm": "float64",
        "product_width_cm": "float64",
    },
    "order_payments": {
        "order_id": "string",
        "payment_sequential": "int64",
        "payment_type": "string",
        "payment_installments": "int64",
        "payment_value": "float64",
    },
    "order_reviews": {
        "review_id": "string",
        "order_id": "string",
        "review_score": "int64",
        "review_comment_title": "string",
        "review_comment_message": "string",
    },
    "sellers": {
        "seller_id": "string",
        "seller_zip_code_prefix": "string",
        "seller_city": "string",
        "seller_state": "string",
    },
    "geolocation": {
        "geolocation_zip_code_prefix": "string",
        "geolocation_lat": "float64",
        "geolocation_lng": "float64",
        "geolocation_city": "string",
        "geolocation_state": "string",
    },
    "product_category_translation": {
        "product_category_name": "string",
        "product_category_name_english": "string",
    },
}


def _read_csv(table_name: str, raw_dir: Path) -> pd.DataFrame:
    """Read a single raw CSV into a DataFrame with dtypes/dates applied."""
    path = raw_dir / RAW_FILES[table_name]
    if not path.exists():
        raise FileNotFoundError(
            f"Missing raw data file for '{table_name}': {path}\n"
            "Place the Kaggle CSVs in data/raw/ (see README) before running the pipeline."
        )

    df = pd.read_csv(
        path,
        dtype=_DTYPES.get(table_name),
        parse_dates=_DATE_COLUMNS.get(table_name, []),
    )
    logger.info("Extracted %-30s %6d rows, %2d cols from %s", table_name, len(df), df.shape[1], path.name)
    return df


def extract_all(raw_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """
    Read all 9 raw Olist CSVs into a dict of DataFrames keyed by table name.

    Raises FileNotFoundError (with a clear message) if data/raw/ is missing
    or incomplete — callers should let this propagate up to the pipeline
    runner, which reports it cleanly rather than a stack trace.
    """
    raw_dir = raw_dir or RAW_DATA_DIR

    if not raw_dir.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {raw_dir}\n"
            "Download the Kaggle 'Brazilian E-Commerce Public Dataset by Olist' "
            "and place its CSVs in data/raw/ before running the pipeline."
        )

    return {name: _read_csv(name, raw_dir) for name in RAW_FILES}
