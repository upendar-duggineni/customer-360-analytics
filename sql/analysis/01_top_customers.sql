SELECT
    customer_id,
    customer_city,
    customer_state,
    total_orders,
    total_revenue,
    average_order_value
FROM customer360_view
ORDER BY total_revenue DESC
LIMIT 10;