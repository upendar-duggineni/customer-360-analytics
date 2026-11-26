-- Customer 360 analytical view
-- Payments and reviews are aggregated independently at order grain.
-- This prevents multi-payment and multi-review orders from multiplying revenue.

DROP VIEW IF EXISTS customer360_view;

CREATE VIEW customer360_view AS
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_value
    FROM payments
    GROUP BY order_id
),
review_by_order AS (
    SELECT
        order_id,
        AVG(review_score)::numeric AS order_average_rating
    FROM reviews
    GROUP BY order_id
),
order_level AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_purchase_timestamp,
        COALESCE(p.order_payment_value, 0) AS order_payment_value,
        r.order_average_rating
    FROM orders o
    LEFT JOIN payment_by_order p
        ON o.order_id = p.order_id
    LEFT JOIN review_by_order r
        ON o.order_id = r.order_id
)
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    COUNT(DISTINCT ol.order_id) AS total_orders,
    ROUND(COALESCE(SUM(ol.order_payment_value), 0), 2) AS total_revenue,
    ROUND(
        COALESCE(SUM(ol.order_payment_value), 0)
        / NULLIF(COUNT(DISTINCT ol.order_id), 0),
        2
    ) AS average_order_value,
    MAX(ol.order_purchase_timestamp) AS last_purchase_date,
    ROUND(AVG(ol.order_average_rating), 2) AS average_review_score
FROM customers c
LEFT JOIN order_level ol
    ON c.customer_id = ol.customer_id
GROUP BY
    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state;

