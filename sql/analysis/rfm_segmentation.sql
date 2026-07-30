-- ============================================================================
-- rfm_segmentation.sql
-- ----------------------------------------------------------------------------
-- Business question: Which customers are our most/least valuable, and how
-- should we group them for targeted marketing (win-back campaigns, loyalty
-- perks, churn-risk outreach)?
--
-- Approach: classic RFM (Recency, Frequency, Monetary) analysis, computed
-- at the *person* level via customers.customer_unique_id — NOT customer_id,
-- since Olist mints a fresh customer_id for every order and customer_id
-- alone would make every customer look like a one-time buyer. Recency is
-- days between each customer's most recent delivered order and the dataset's
-- max order date (used as a stand-in "today" since this is historical data).
-- Each of R/F/M is scored 1-5 via NTILE(5) (5 = best), summed into an
-- rfm_score, and mapped to a named segment. Two result sets:
--   1. rfm_customers — one row per customer_unique_id with scores/segment
--   2. rfm_segment_summary — customer counts and revenue per segment
-- ============================================================================

-- @name: rfm_customers
WITH delivered_orders AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        o.order_purchase_timestamp
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
),
order_value AS (
    SELECT
        d.order_id,
        d.customer_unique_id,
        d.order_purchase_timestamp,
        SUM(p.payment_value) AS order_revenue
    FROM delivered_orders d
    JOIN order_payments p ON p.order_id = d.order_id
    GROUP BY d.order_id, d.customer_unique_id, d.order_purchase_timestamp
),
snapshot AS (
    SELECT MAX(order_purchase_timestamp) AS max_date FROM order_value
),
customer_rfm AS (
    SELECT
        ov.customer_unique_id,
        DATE_DIFF('day', MAX(ov.order_purchase_timestamp), MAX(s.max_date)) AS recency_days,
        COUNT(DISTINCT ov.order_id)                                          AS frequency,
        SUM(ov.order_revenue)                                                AS monetary
    FROM order_value ov
    CROSS JOIN snapshot s
    GROUP BY ov.customer_unique_id
),
scored AS (
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        ROUND(monetary, 2) AS monetary,
        -- recency: fewer days since last purchase = better = higher score
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM customer_rfm
)
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) AS rfm_score,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2                  THEN 'New Customers'
        WHEN r_score >= 3 AND m_score >= 4                  THEN 'Big Spenders'
        WHEN r_score <= 2 AND f_score >= 4                  THEN 'At Risk'
        WHEN r_score <= 2 AND m_score >= 4                  THEN 'Cant Lose Them'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2  THEN 'Hibernating'
        ELSE 'Needs Attention'
    END AS segment
FROM scored;

-- @name: rfm_segment_summary
WITH delivered_orders AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        o.order_purchase_timestamp
    FROM orders o
    JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
),
order_value AS (
    SELECT
        d.order_id,
        d.customer_unique_id,
        d.order_purchase_timestamp,
        SUM(p.payment_value) AS order_revenue
    FROM delivered_orders d
    JOIN order_payments p ON p.order_id = d.order_id
    GROUP BY d.order_id, d.customer_unique_id, d.order_purchase_timestamp
),
snapshot AS (
    SELECT MAX(order_purchase_timestamp) AS max_date FROM order_value
),
customer_rfm AS (
    SELECT
        ov.customer_unique_id,
        DATE_DIFF('day', MAX(ov.order_purchase_timestamp), MAX(s.max_date)) AS recency_days,
        COUNT(DISTINCT ov.order_id)                                          AS frequency,
        SUM(ov.order_revenue)                                                AS monetary
    FROM order_value ov
    CROSS JOIN snapshot s
    GROUP BY ov.customer_unique_id
),
scored AS (
    SELECT
        customer_unique_id,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM customer_rfm
),
segmented AS (
    SELECT
        customer_unique_id,
        monetary,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2                  THEN 'New Customers'
            WHEN r_score >= 3 AND m_score >= 4                  THEN 'Big Spenders'
            WHEN r_score <= 2 AND f_score >= 4                  THEN 'At Risk'
            WHEN r_score <= 2 AND m_score >= 4                  THEN 'Cant Lose Them'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2  THEN 'Hibernating'
            ELSE 'Needs Attention'
        END AS segment
    FROM scored
)
SELECT
    segment,
    COUNT(*)                       AS customer_count,
    ROUND(SUM(monetary), 2)        AS total_revenue,
    ROUND(AVG(monetary), 2)        AS avg_revenue_per_customer
FROM segmented
GROUP BY segment
ORDER BY total_revenue DESC;
