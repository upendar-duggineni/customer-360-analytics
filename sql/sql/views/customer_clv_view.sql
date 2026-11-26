CREATE OR REPLACE VIEW public.customer_clv_view AS
WITH customer_value AS (
    SELECT
        customer_unique_id,
        SUM(payment_value)::numeric(14,2) AS historical_delivered_value
    FROM public.order_facts
    WHERE is_revenue_order = TRUE
    GROUP BY customer_unique_id
)
SELECT
    customer_unique_id,
    historical_delivered_value,
    NTILE(10) OVER (
        ORDER BY historical_delivered_value DESC
    ) AS clv_decile
FROM customer_value;