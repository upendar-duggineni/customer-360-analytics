DROP VIEW IF EXISTS customer360_view;

CREATE VIEW customer360_view AS

SELECT

    c.customer_id,

    c.customer_unique_id,

    c.customer_city,

    c.customer_state,

    COUNT(DISTINCT o.order_id) AS total_orders,

    ROUND(COALESCE(SUM(p.payment_value), 0), 2) AS total_revenue,

    ROUND(COALESCE(AVG(p.payment_value), 0), 2) AS average_order_value,

    MAX(o.order_purchase_timestamp) AS last_purchase_date,

    ROUND(COALESCE(AVG(r.review_score), 0), 2) AS average_review_score

FROM customers c

LEFT JOIN orders o
ON c.customer_id = o.customer_id

LEFT JOIN payments p
ON o.order_id = p.order_id

LEFT JOIN reviews r
ON o.order_id = r.order_id

GROUP BY

    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state;