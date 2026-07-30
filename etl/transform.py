"""
transform.py — cleaning and enrichment of the raw Olist DataFrames.

Responsibilities:
  * trim whitespace on string columns
  * drop exact-duplicate rows (raw Olist data has a handful, notably in
    order_reviews and geolocation)
  * translate product_category_name -> English, keeping the original column
  * derive helper columns:
      - orders.order_purchase_month  ('YYYY-MM')
      - orders.delivery_delay_days   (delivered_customer_date - estimated_delivery_date;
                                       positive = late, negative = early)
  * sensible handling of missing values (documented per table below; we do
    NOT silently impute numeric business data — we leave true NaNs as NULL
    and let downstream SQL/BI tooling decide how to treat them)
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _trim_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from every string/object column."""
    df = df.copy()
    for col in df.select_dtypes(include=["string", "object"]).columns:
        df[col] = df[col].str.strip()
    return df


def _dedupe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Drop exact-duplicate rows, logging how many were removed."""
    before = len(df)
    df = df.drop_duplicates()
    removed = before - len(df)
    if removed:
        logger.info("Deduped %-30s removed %d exact-duplicate rows", table_name, removed)
    return df


def transform_products(products: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    """Attach the English category translation while keeping the Portuguese original."""
    df = _trim_strings(products)
    df = _dedupe(df, "products")

    df = df.merge(
        translation[["product_category_name", "product_category_name_english"]],
        on="product_category_name",
        how="left",
    )

    missing_translation = df["product_category_name"].notna() & df["product_category_name_english"].isna()
    if missing_translation.any():
        logger.warning(
            "products: %d rows have a category name with no English translation",
            missing_translation.sum(),
        )

    return df


def transform_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Clean orders and derive purchase-month / delivery-delay helper columns."""
    df = _trim_strings(orders)
    df = _dedupe(df, "orders")

    df["order_purchase_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)

    # Delay is only meaningful once the order has actually been delivered.
    delivered = df["order_delivered_customer_date"].notna() & df["order_estimated_delivery_date"].notna()
    df["delivery_delay_days"] = pd.NA
    df.loc[delivered, "delivery_delay_days"] = (
        df.loc[delivered, "order_delivered_customer_date"] - df.loc[delivered, "order_estimated_delivery_date"]
    ).dt.days
    df["delivery_delay_days"] = df["delivery_delay_days"].astype("Int64")

    n_undelivered = (~delivered).sum()
    logger.info(
        "orders: derived order_purchase_month and delivery_delay_days "
        "(%d/%d orders have no delivery date yet, delay left NULL)",
        n_undelivered,
        len(df),
    )

    return df


def transform_order_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """
    Clean reviews. review_id is not unique in the raw data (a review can be
    resubmitted), so we only drop *exact* row duplicates rather than
    deduping on review_id alone — collapsing on review_id would silently
    discard legitimate re-review history.
    """
    df = _trim_strings(reviews)
    df = _dedupe(df, "order_reviews")
    return df


def transform_geolocation(geo: pd.DataFrame) -> pd.DataFrame:
    """
    Clean geolocation. This table has no natural primary key (many rows per
    zip prefix); we only remove exact duplicate rows, which are common in
    the raw file (repeated identical lat/lng/city/state for the same prefix).
    """
    df = _trim_strings(geo)
    df = _dedupe(df, "geolocation")
    return df


def transform_generic(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Default cleaning path for tables with no special handling: trim + dedupe."""
    df = _trim_strings(df)
    df = _dedupe(df, table_name)
    return df


def transform_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Apply cleaning/enrichment to every extracted table and return a dict of
    cleaned DataFrames ready for loading, keyed the same as extract_all().
    """
    cleaned: dict[str, pd.DataFrame] = {}

    translation = transform_generic(
        raw["product_category_translation"], "product_category_translation"
    )
    # The source translation file is incomplete (e.g. 'pc_gamer'); add the missing
    # categories with the Portuguese name as fallback so the products FK holds.
    product_cats = raw["products"]["product_category_name"].dropna().str.strip().unique()
    missing = sorted(set(product_cats) - set(translation["product_category_name"]))
    if missing:
        translation = pd.concat(
            [translation, pd.DataFrame({
                "product_category_name": missing,
                "product_category_name_english": missing,
            })],
            ignore_index=True,
        )
    cleaned["product_category_translation"] = translation
    cleaned["products"] = transform_products(raw["products"], cleaned["product_category_translation"])
    cleaned["customers"] = transform_generic(raw["customers"], "customers")
    cleaned["sellers"] = transform_generic(raw["sellers"], "sellers")
    cleaned["geolocation"] = transform_geolocation(raw["geolocation"])
    cleaned["orders"] = transform_orders(raw["orders"])
    cleaned["order_items"] = transform_generic(raw["order_items"], "order_items")
    cleaned["order_payments"] = transform_generic(raw["order_payments"], "order_payments")
    cleaned["order_reviews"] = transform_order_reviews(raw["order_reviews"])

    return cleaned
