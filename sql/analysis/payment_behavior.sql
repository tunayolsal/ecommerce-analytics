-- ============================================================================
-- payment_behavior.sql
-- ----------------------------------------------------------------------------
-- Business question: How do customers pay — which payment methods dominate,
-- how common are installment plans, and does credit-card installment usage
-- vary by product category (useful for financing/promo strategy)?
--
-- Approach: uses order_payments directly (payment rows, not orders — an
-- order can have multiple payment rows). Four result sets:
--   1. payment_type_mix              — share of payment rows/revenue by type
--   2. installment_distribution      — count/share of payments by installment count
--   3. avg_payment_value_by_installments — avg payment_value per installment bucket
--   4. credit_card_installments_by_category — avg installments & value for
--      credit-card payments, broken down by product category
-- ============================================================================

-- @name: payment_type_mix
WITH totals AS (
    SELECT
        payment_type,
        COUNT(*)                    AS payment_count,
        SUM(payment_value)          AS total_value
    FROM order_payments
    GROUP BY payment_type
)
SELECT
    payment_type,
    payment_count,
    ROUND(100.0 * payment_count / SUM(payment_count) OVER (), 2) AS pct_of_payments,
    ROUND(total_value, 2)                                         AS total_revenue,
    ROUND(100.0 * total_value / SUM(total_value) OVER (), 2)     AS pct_of_revenue
FROM totals
ORDER BY total_revenue DESC;

-- @name: installment_distribution
SELECT
    payment_installments,
    COUNT(*)                                                      AS payment_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)            AS pct_of_payments,
    ROUND(SUM(payment_value), 2)                                  AS total_revenue
FROM order_payments
GROUP BY payment_installments
ORDER BY payment_installments;

-- @name: avg_payment_value_by_installments
SELECT
    payment_installments,
    COUNT(*)                        AS payment_count,
    ROUND(AVG(payment_value), 2)    AS avg_payment_value
FROM order_payments
WHERE payment_type = 'credit_card'
GROUP BY payment_installments
ORDER BY payment_installments;

-- @name: credit_card_installments_by_category
WITH cc_payments AS (
    SELECT order_id, payment_installments, payment_value
    FROM order_payments
    WHERE payment_type = 'credit_card'
),
order_category AS (
    -- one representative category per order: the category of its
    -- highest-priced line item, to avoid fan-out from multi-item orders
    SELECT
        order_id,
        product_id,
        ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY price DESC) AS rn
    FROM order_items
)
SELECT
    COALESCE(pr.product_category_name_english, 'unknown') AS category,
    COUNT(*)                                                AS payment_count,
    ROUND(AVG(cc.payment_installments), 2)                  AS avg_installments,
    ROUND(AVG(cc.payment_value), 2)                         AS avg_payment_value
FROM cc_payments cc
JOIN order_category oc ON oc.order_id = cc.order_id AND oc.rn = 1
LEFT JOIN products pr ON pr.product_id = oc.product_id
GROUP BY category
HAVING COUNT(*) >= 30
ORDER BY avg_installments DESC
LIMIT 20;
