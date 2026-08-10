SELECT
    c.customer_state,
    ROUND(SUM(p.payment_value), 2) AS total_revenue,
    COUNT(DISTINCT o.order_id) AS total_orders
FROM customers c
JOIN orders o
ON c.customer_id = o.customer_id
JOIN payments p
ON o.order_id = p.order_id
GROUP BY c.customer_state
ORDER BY total_revenue 