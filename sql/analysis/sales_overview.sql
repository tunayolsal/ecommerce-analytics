-- ============================================================================
-- sales_overview.sql
-- ----------------------------------------------------------------------------
-- Business question: What does the top-line health of the business look
-- like — how is revenue trending month over month, what's the average
-- order value, which product categories and states drive the most revenue?
--
-- Approach: revenue is measured on order_payments.payment_value (what the
-- customer actually paid, including freight and installment surcharges)
-- rather than order_items.price, since payment_value is the cleanest
-- single "money in the door" figure. Orders are restricted to
-- order_status = 'delivered' throughout so cancelled/unfulfilled orders
-- don't inflate revenue. Four result sets are returned (split into
-- separate queries with `-- @name:` markers so etl/export_marts.py can
-- export each to its own parquet file):
--   1. monthly_revenue_trend  — revenue, order count, AOV by month
--   2. revenue_by_category    — top 15 product categories by revenue
--   3. revenue_by_state       — revenue by customer state
-- ============================================================================

-- @name: monthly_revenue_trend
WITH order_revenue AS (
    SELECT
        o.order_id,
        o.order_purchase_month,
        SUM(p.payment_value) AS order_revenue
    FROM orders o
    JOIN order_payments p ON p.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.order_id, o.order_purchase_month
)
SELECT
    order_purchase_month,
    COUNT(*)                              AS order_count,
    ROUND(SUM(order_revenue), 2)          AS total_revenue,
    ROUND(AVG(order_revenue), 2)          AS avg_order_value
FROM order_revenue
GROUP BY order_purchase_month
ORDER BY order_purchase_month;

-- @name: revenue_by_category
WITH order_revenue AS (
    SELECT
        o.order_id,
        SUM(p.payment_value) AS order_revenue
    FROM orders o
    JOIN order_payments p ON p.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.order_id
),
-- allocate each order's total payment across its line items proportionally
-- to item price, so payment (which includes freight) attributes fairly to
-- category rather than double counting per-item price.
item_share AS (
    SELECT
        oi.order_id,
        oi.product_id,
        oi.price,
        oi.price / NULLIF(SUM(oi.price) OVER (PARTITION BY oi.order_id), 0) AS price_share
    FROM order_items oi
),
category_revenue AS (
    SELECT
        COALESCE(pr.product_category_name_english, 'unknown') AS category,
        s.price_share * r.order_revenue AS allocated_revenue
    FROM item_share s
    JOIN order_revenue r ON r.order_id = s.order_id
    LEFT JOIN products pr ON pr.product_id = s.product_id
)
SELECT
    category,
    ROUND(SUM(allocated_revenue), 2) AS total_revenue,
    COUNT(*)                          AS line_items
FROM category_revenue
GROUP BY category
ORDER BY total_revenue DESC
LIMIT 15;

-- @name: revenue_by_state
SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id)            AS order_count,
    ROUND(SUM(p.payment_value), 2)        AS total_revenue,
    ROUND(SUM(p.payment_value) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN order_payments p ON p.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY total_revenue DESC;
