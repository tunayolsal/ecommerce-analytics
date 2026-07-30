-- ============================================================================
-- Olist Brazilian E-Commerce — Data Warehouse Schema
-- ----------------------------------------------------------------------------
-- Written in PostgreSQL-compatible dialect (works unchanged in DuckDB, which
-- speaks a close-to-Postgres SQL surface). Loaded by etl/load.py into
-- data/olist.duckdb.
--
-- Source: Kaggle "Brazilian E-Commerce Public Dataset by Olist"
-- https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
--
-- Notes on data-integrity caveats (kept honest rather than forcing keys that
-- don't hold in the raw data):
--   * olist_geolocation: no natural primary key — the same zip-code prefix
--     appears many times with slightly different lat/lng (multiple
--     addresses share a prefix). Modeled as a plain fact table, no PK.
--   * olist_order_reviews: review_id is NOT unique in the raw CSV (a review
--     can be re-submitted / updated, producing duplicate review_id rows with
--     different comments/timestamps). We do NOT declare review_id PRIMARY
--     KEY; instead we use a composite natural key (review_id, order_id) and
--     de-duplicate exact row duplicates in the transform step.
--   * FKs are declared for documentation / query-planning purposes. DuckDB
--     does not enforce FK constraints at insert time, so load.py is
--     responsible for referential sanity checks (see run_pipeline.py's
--     data-quality section).
-- ============================================================================

DROP TABLE IF EXISTS order_reviews;
DROP TABLE IF EXISTS order_payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS geolocation;
DROP TABLE IF EXISTS product_category_translation;

-- ----------------------------------------------------------------------------
-- product_category_name_translation.csv
-- ----------------------------------------------------------------------------
CREATE TABLE product_category_translation (
    product_category_name          VARCHAR PRIMARY KEY,
    product_category_name_english  VARCHAR NOT NULL
);

-- ----------------------------------------------------------------------------
-- olist_customers_dataset.csv
-- One row per unique customer *order* (customer_id changes per order; the
-- stable person-level identifier is customer_unique_id).
-- ----------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id               VARCHAR PRIMARY KEY,
    customer_unique_id         VARCHAR NOT NULL,
    customer_zip_code_prefix   VARCHAR NOT NULL,
    customer_city              VARCHAR NOT NULL,
    customer_state              VARCHAR NOT NULL
);

-- ----------------------------------------------------------------------------
-- olist_sellers_dataset.csv
-- ----------------------------------------------------------------------------
CREATE TABLE sellers (
    seller_id                  VARCHAR PRIMARY KEY,
    seller_zip_code_prefix     VARCHAR NOT NULL,
    seller_city                VARCHAR NOT NULL,
    seller_state                VARCHAR NOT NULL
);

-- ----------------------------------------------------------------------------
-- olist_geolocation_dataset.csv
-- No PK: many rows share the same zip prefix (see caveat above).
-- ----------------------------------------------------------------------------
CREATE TABLE geolocation (
    geolocation_zip_code_prefix VARCHAR NOT NULL,
    geolocation_lat              DOUBLE,
    geolocation_lng              DOUBLE,
    geolocation_city             VARCHAR,
    geolocation_state             VARCHAR
);

-- ----------------------------------------------------------------------------
-- olist_products_dataset.csv
-- ----------------------------------------------------------------------------
CREATE TABLE products (
    product_id                     VARCHAR PRIMARY KEY,
    product_category_name          VARCHAR,
    product_category_name_english  VARCHAR,
    product_name_lenght             INTEGER,
    product_description_lenght      INTEGER,
    product_photos_qty              INTEGER,
    product_weight_g                 DOUBLE,
    product_length_cm                DOUBLE,
    product_height_cm                DOUBLE,
    product_width_cm                  DOUBLE,
    FOREIGN KEY (product_category_name) REFERENCES product_category_translation (product_category_name)
);

-- ----------------------------------------------------------------------------
-- olist_orders_dataset.csv
-- ----------------------------------------------------------------------------
CREATE TABLE orders (
    order_id                        VARCHAR PRIMARY KEY,
    customer_id                     VARCHAR NOT NULL,
    order_status                    VARCHAR NOT NULL,
    order_purchase_timestamp         TIMESTAMP,
    order_approved_at                TIMESTAMP,
    order_delivered_carrier_date     TIMESTAMP,
    order_delivered_customer_date    TIMESTAMP,
    order_estimated_delivery_date    TIMESTAMP,
    order_purchase_month             VARCHAR,   -- derived: 'YYYY-MM', helper for monthly rollups
    delivery_delay_days              INTEGER,   -- derived: delivered_customer_date - estimated_delivery_date
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

-- ----------------------------------------------------------------------------
-- olist_order_items_dataset.csv
-- Composite natural key: (order_id, order_item_id)
-- ----------------------------------------------------------------------------
CREATE TABLE order_items (
    order_id             VARCHAR NOT NULL,
    order_item_id         INTEGER NOT NULL,
    product_id            VARCHAR NOT NULL,
    seller_id              VARCHAR NOT NULL,
    shipping_limit_date     TIMESTAMP,
    price                    DOUBLE NOT NULL,
    freight_value             DOUBLE NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id),
    FOREIGN KEY (seller_id) REFERENCES sellers (seller_id)
);

-- ----------------------------------------------------------------------------
-- olist_order_payments_dataset.csv
-- Composite natural key: (order_id, payment_sequential) — an order can be
-- paid with multiple installments/payment methods.
-- ----------------------------------------------------------------------------
CREATE TABLE order_payments (
    order_id                VARCHAR NOT NULL,
    payment_sequential        INTEGER NOT NULL,
    payment_type                VARCHAR NOT NULL,
    payment_installments         INTEGER NOT NULL,
    payment_value                 DOUBLE NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- ----------------------------------------------------------------------------
-- olist_order_reviews_dataset.csv
-- review_id is NOT globally unique in the source data — no PRIMARY KEY on it
-- alone. See caveat note at top of file.
-- ----------------------------------------------------------------------------
CREATE TABLE order_reviews (
    review_id                  VARCHAR NOT NULL,
    order_id                    VARCHAR NOT NULL,
    review_score                  INTEGER NOT NULL,
    review_comment_title           VARCHAR,
    review_comment_message          VARCHAR,
    review_creation_date              TIMESTAMP,
    review_answer_timestamp            TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);
