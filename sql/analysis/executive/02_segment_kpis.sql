SELECT
    customer_segment,

    COUNT(*) AS customer_count,

    ROUND(SUM(monetary), 2) AS total_revenue,

    ROUND(AVG(monetary), 2) AS average_customer_value,

    ROUND(AVG(frequency), 2) AS average_purchase_frequency,

    ROUND(AVG(rfm_total_score), 2) AS average_rfm_score

FROM customer_rfm_view

GROUP BY customer_segment

ORDER BY total_revenue DESC;