SELECT
    pr.product_category_name,
    COUNT(oi.product_id) AS products_sold,
    ROUND(SUM(oi.price), 2) AS total_sales
FROM order_items oi
JOIN products pr
ON oi.product_id = pr.product_id
GROUP BY pr.product_category_name
ORDER BY total_sales DESC
LIMIT 10;