-- ============================================================================
-- cohort_retention.sql
-- ----------------------------------------------------------------------------
-- Business question: Once we acquire a customer in a given month, how many
-- of them come back and buy again in subsequent months? Olist is known to
-- have very low repeat-purchase rates — this quantifies it.
--
-- Approach: cohort each customer_unique_id by the calendar month of their
-- first delivered order (acquisition month). For every subsequent order,
-- compute "months since first purchase" (0 = acquisition month itself).
-- Build a cohort x month-offset retention matrix showing the % of the
-- original cohort still active. Two result sets:
--   1. cohort_retention_matrix — cohort_month, months_since_first, customers
--      active, retention_pct (vs. that cohort's month-0 size)
--   2. cohort_sizes — acquisition-month cohort sizes (for reference/chart axis)
-- ============================================================================

-- @name: cohort_retention_matrix
WITH delivered_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
),
first_purchase AS (
    SELECT
        customer_unique_id,
        MIN(DATE_TRUNC('month', order_purchase_timestamp)) AS cohort_month
    FROM delivered_orders
    GROUP BY customer_unique_id
),
order_months AS (
    SELECT DISTINCT
        d.customer_unique_id,
        DATE_TRUNC('month', d.order_purchase_timestamp) AS order_month
    FROM delivered_orders d
),
cohort_activity AS (
    SELECT
        f.cohort_month,
        om.customer_unique_id,
        DATE_DIFF('month', f.cohort_month, om.order_month) AS months_since_first
    FROM order_months om
    JOIN first_purchase f ON f.customer_unique_id = om.customer_unique_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_size
    FROM cohort_activity
    WHERE months_since_first = 0
    GROUP BY cohort_month
),
matrix AS (
    SELECT
        cohort_month,
        months_since_first,
        COUNT(DISTINCT customer_unique_id) AS active_customers
    FROM cohort_activity
    GROUP BY cohort_month, months_since_first
)
SELECT
    m.cohort_month,
    m.months_since_first,
    m.active_customers,
    s.cohort_size,
    ROUND(100.0 * m.active_customers / NULLIF(s.cohort_size, 0), 2) AS retention_pct
FROM matrix m
JOIN cohort_sizes s ON s.cohort_month = m.cohort_month
ORDER BY m.cohort_month, m.months_since_first;

-- @name: cohort_sizes
WITH delivered_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_purchase_timestamp
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
),
first_purchase AS (
    SELECT
        customer_unique_id,
        MIN(DATE_TRUNC('month', order_purchase_timestamp)) AS cohort_month
    FROM delivered_orders
    GROUP BY customer_unique_id
)
SELECT
    cohort_month,
    COUNT(*) AS cohort_size
FROM first_purchase
GROUP BY cohort_month
ORDER BY cohort_month;
