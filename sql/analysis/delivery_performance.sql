-- ============================================================================
-- delivery_performance.sql
-- ----------------------------------------------------------------------------
-- Business question: How reliable is our delivery promise, does lateness
-- vary by geography, and does a late delivery hurt customer satisfaction
-- (review scores)?
--
-- Approach: uses the pre-derived orders.delivery_delay_days (actual minus
-- estimated delivery date; negative/zero = on-time or early, positive =
-- late). Restricted to delivered orders with a non-null delivery date.
-- Three result sets:
--   1. delivery_rate_overall     — on-time vs late counts/rates, avg delay
--   2. delivery_delay_by_state   — delay distribution per customer state
--   3. review_score_by_delivery  — avg review_score for late vs on-time orders
-- ============================================================================

-- @name: delivery_rate_overall
WITH delivered AS (
    SELECT
        order_id,
        delivery_delay_days,
        CASE WHEN delivery_delay_days > 0 THEN 'late' ELSE 'on_time' END AS delivery_status
    FROM orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
)
SELECT
    delivery_status,
    COUNT(*)                                                     AS order_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)           AS pct_of_orders,
    ROUND(AVG(delivery_delay_days), 2)                           AS avg_delay_days
FROM delivered
GROUP BY delivery_status
ORDER BY delivery_status;

-- @name: delivery_delay_by_state
WITH delivered AS (
    SELECT
        o.order_id,
        c.customer_state,
        o.delivery_delay_days,
        CASE WHEN o.delivery_delay_days > 0 THEN 1 ELSE 0 END AS is_late
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
)
SELECT
    customer_state,
    COUNT(*)                                    AS order_count,
    ROUND(AVG(delivery_delay_days), 2)          AS avg_delay_days,
    ROUND(100.0 * SUM(is_late) / COUNT(*), 2)   AS late_pct
FROM delivered
GROUP BY customer_state
ORDER BY late_pct DESC;

-- @name: review_score_by_delivery
WITH delivered AS (
    SELECT
        order_id,
        CASE WHEN delivery_delay_days > 0 THEN 'late' ELSE 'on_time' END AS delivery_status
    FROM orders
    WHERE order_status = 'delivered'
      AND order_delivered_customer_date IS NOT NULL
)
SELECT
    d.delivery_status,
    COUNT(*)                          AS review_count,
    ROUND(AVG(r.review_score), 2)     AS avg_review_score,
    ROUND(100.0 * SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_bad_reviews
FROM delivered d
JOIN order_reviews r ON r.order_id = d.order_id
GROUP BY d.delivery_status
ORDER BY d.delivery_status;
