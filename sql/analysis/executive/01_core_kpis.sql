SELECT
    ROUND(
        (SELECT SUM(payment_value) FROM payments),
        2
    ) AS total_revenue,

    (
        SELECT COUNT(DISTINCT order_id)
        FROM orders
    ) AS total_orders,

    (
        SELECT COUNT(DISTINCT customer_unique_id)
        FROM customers
    ) AS total_customers,

    ROUND(
        (SELECT SUM(payment_value) FROM payments)
        /
        NULLIF(
            (SELECT COUNT(DISTINCT order_id) FROM orders),
            0
        ),
        2
    ) AS average_order_value,

    ROUND(
        (SELECT AVG(review_score) FROM reviews),
        2
    ) AS average_rating;