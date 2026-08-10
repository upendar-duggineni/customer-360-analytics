DROP VIEW IF EXISTS customer_rfm_view;

CREATE VIEW customer_rfm_view AS

WITH customer_metrics AS (

    SELECT
        c.customer_unique_id,

        MAX(o.order_purchase_timestamp)::date AS last_purchase_date,

        COUNT(DISTINCT o.order_id) AS frequency,

        ROUND(SUM(p.payment_value), 2) AS monetary

    FROM customers c

    JOIN orders o
        ON c.customer_id = o.customer_id

    JOIN payments p
        ON o.order_id = p.order_id

    WHERE o.order_status = 'delivered'

    GROUP BY c.customer_unique_id
),

rfm_scores AS (

    SELECT
        customer_unique_id,
        last_purchase_date,
        frequency,
        monetary,

        NTILE(5) OVER (
            ORDER BY last_purchase_date DESC
        ) AS recency_score,

        NTILE(5) OVER (
            ORDER BY frequency
        ) AS frequency_score,

        NTILE(5) OVER (
            ORDER BY monetary
        ) AS monetary_score

    FROM customer_metrics
)

SELECT
    customer_unique_id,
    last_purchase_date,
    frequency,
    monetary,
    recency_score,
    frequency_score,
    monetary_score,

    (
        recency_score
        + frequency_score
        + monetary_score
    ) AS rfm_total_score,

    CASE

        WHEN recency_score >= 4
         AND frequency_score >= 4
         AND monetary_score >= 4
            THEN 'Champions'

        WHEN recency_score >= 3
         AND frequency_score >= 3
         AND monetary_score >= 3
            THEN 'Loyal Customers'

        WHEN recency_score >= 4
         AND frequency_score <= 2
            THEN 'Potential Loyalists'

        WHEN recency_score <= 2
         AND frequency_score >= 3
         AND monetary_score >= 3
            THEN 'At Risk'

        WHEN recency_score <= 2
         AND frequency_score <= 2
         AND monetary_score <= 2
            THEN 'Hibernating'

        ELSE 'Needs Attention'

    END AS customer_segment

FROM rfm_scores

ORDER BY monetary DESC;