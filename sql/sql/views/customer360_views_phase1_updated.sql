-- Customer 360 Analytics Platform
-- Phase 1: order-level facts and supporting 360 views
-- Designed for the confirmed public-schema Olist tables.
--
-- IMPORTANT:
-- 1. Run against the customer360 database.
-- 2. This script creates/replaces VIEWS only. It does not modify base tables.
-- 3. Review the definitions before execution. Run in pgAdmin Query Tool.
-- 4. Existing customer360_view and customer_rfm_view are replaced with
--    corrected definitions. Their existing output columns are retained;
--    new columns are appended.

BEGIN;

-- ---------------------------------------------------------------------
-- 1. One row per order. Payments and reviews are aggregated separately
--    before joining, preventing payment x review row multiplication.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW public.order_facts AS
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value)::numeric(14,2) AS payment_value
    FROM public.payments
    GROUP BY order_id
),
review_by_order AS (
    SELECT
        order_id,
        AVG(review_score)::numeric(4,2) AS review_score
    FROM public.reviews
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    o.order_status,
    (o.order_status = 'delivered') AS is_revenue_order,
    COALESCE(p.payment_value, 0)::numeric(14,2) AS payment_value,
    r.review_score,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date
FROM public.orders o
JOIN public.customers c
  ON c.customer_id = o.customer_id
LEFT JOIN payment_by_order p
  ON p.order_id = o.order_id
LEFT JOIN review_by_order r
  ON r.order_id = o.order_id;


-- ---------------------------------------------------------------------
-- 2. Customer 360: one row per real customer (customer_unique_id).
--    Delivered metrics are separated from all orders placed.
--    customer_id is retained for compatibility, but represents one
--    associated customer_id only; it is not a customer-level identifier.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW public.customer360_view AS
SELECT
    MIN(c.customer_id)::varchar(50) AS customer_id,
    c.customer_unique_id,
    (ARRAY_AGG(c.customer_city ORDER BY c.customer_id))[1] AS customer_city,
    (ARRAY_AGG(c.customer_state ORDER BY c.customer_id))[1] AS customer_state,
    COUNT(*) FILTER (WHERE o.order_status = 'delivered')::bigint AS total_orders,
    COALESCE(
        SUM(f.payment_value) FILTER (WHERE f.is_revenue_order),
        0
    )::numeric(14,2) AS total_revenue,
    COALESCE(
        SUM(f.payment_value) FILTER (WHERE f.is_revenue_order)
        / NULLIF(COUNT(*) FILTER (WHERE f.is_revenue_order), 0),
        0
    )::numeric(14,2) AS average_order_value,
    MAX(o.order_purchase_timestamp)
        FILTER (WHERE o.order_status = 'delivered') AS last_purchase_date,
    COALESCE(
        AVG(f.review_score) FILTER (WHERE f.is_revenue_order),
        0
    )::numeric(4,2) AS average_review_score,
    COUNT(o.order_id)::bigint AS orders_placed
FROM public.customers c
LEFT JOIN public.orders o
  ON o.customer_id = c.customer_id
LEFT JOIN public.order_facts f
  ON f.order_id = o.order_id
GROUP BY c.customer_unique_id;


-- ---------------------------------------------------------------------
-- 3. RFM: delivered orders only. Recency is measured against the latest
--    delivered purchase date in the dataset (dataset snapshot), not today.
--    Existing output columns are retained; recency_days is appended.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW public.customer_rfm_view AS
WITH dataset_reference AS (
    SELECT MAX(order_purchase_timestamp)::date AS reference_date
    FROM public.order_facts
    WHERE is_revenue_order
),
customer_metrics AS (
    SELECT
        f.customer_unique_id,
        MAX(f.order_purchase_timestamp)::date AS last_purchase_date,
        COUNT(*)::bigint AS frequency,
        SUM(f.payment_value)::numeric(14,2) AS monetary
    FROM public.order_facts f
    WHERE f.is_revenue_order
    GROUP BY f.customer_unique_id
),
metrics_with_recency AS (
    SELECT
        cm.*,
        (dr.reference_date - cm.last_purchase_date)::integer AS recency_days
    FROM customer_metrics cm
    CROSS JOIN dataset_reference dr
),
rfm_scores AS (
    SELECT
        customer_unique_id,
        last_purchase_date,
        frequency,
        monetary,
        recency_days,
        NTILE(5) OVER (ORDER BY last_purchase_date ASC) AS recency_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS frequency_score,
        NTILE(5) OVER (ORDER BY monetary ASC) AS monetary_score
    FROM metrics_with_recency
)
SELECT
    customer_unique_id,
    last_purchase_date,
    frequency,
    monetary,
    recency_score,
    frequency_score,
    monetary_score,
    (recency_score + frequency_score + monetary_score)::integer AS rfm_total_score,
    CASE
        WHEN recency_score >= 4 AND frequency_score >= 4 AND monetary_score >= 4
            THEN 'Champions'
        WHEN recency_score >= 3 AND frequency_score >= 3 AND monetary_score >= 3
            THEN 'Loyal Customers'
        WHEN recency_score >= 4 AND frequency_score <= 2
            THEN 'Potential Loyalists'
        WHEN recency_score <= 2 AND frequency_score >= 3 AND monetary_score >= 3
            THEN 'At Risk'
        WHEN recency_score <= 2 AND frequency_score <= 2 AND monetary_score <= 2
            THEN 'Hibernating'
        ELSE 'Needs Attention'
    END::text AS customer_segment,
    recency_days
FROM rfm_scores;


-- ---------------------------------------------------------------------
-- 4. Customer CLV proxy view.
--    This is a historical monetary-value proxy, not a predictive CLV model.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW public.customer_clv_view AS
SELECT
    customer_unique_id,
    monetary AS historical_delivered_value,
    NTILE(10) OVER (ORDER BY monetary DESC)::integer AS clv_decile
FROM public.customer_rfm_view;


-- ---------------------------------------------------------------------
-- 5. Seller performance: delivered product sales only (freight separate).
--    Rating is averaged at order grain; late rate is based on unique orders.
--    `orders`, `item_sales`, `avg_order_rating`, `late_delivery_pct`,
--    and `sales_rank` support the uploaded tests and 360 page.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW public.seller_performance_view AS
WITH seller_order_items AS (
    SELECT
        oi.seller_id,
        oi.order_id,
        SUM(oi.price)::numeric(14,2) AS item_sales
    FROM public.order_items oi
    JOIN public.orders o
      ON o.order_id = oi.order_id
     AND o.order_status = 'delivered'
    GROUP BY oi.seller_id, oi.order_id
),
seller_metrics AS (
    SELECT
        soi.seller_id,
        COUNT(DISTINCT soi.order_id)::bigint AS orders,
        COALESCE(SUM(soi.item_sales), 0)::numeric(14,2) AS item_sales,
        AVG(facts.review_score)::numeric(4,2) AS avg_order_rating,
        (
            100.0 * COUNT(*) FILTER (
                WHERE o.order_delivered_customer_date >
                      o.order_estimated_delivery_date
            ) / NULLIF(COUNT(*), 0)
        )::numeric(6,2) AS late_delivery_pct
    FROM seller_order_items soi
    JOIN public.orders o
      ON o.order_id = soi.order_id
    LEFT JOIN public.order_facts facts
      ON facts.order_id = soi.order_id
    GROUP BY soi.seller_id
)
SELECT
    seller_id,
    orders,
    item_sales,
    avg_order_rating,
    COALESCE(late_delivery_pct, 0)::numeric(6,2) AS late_delivery_pct,
    DENSE_RANK() OVER (ORDER BY item_sales DESC)::bigint AS sales_rank
FROM seller_metrics;

COMMIT;


-- ---------------------------------------------------------------------
-- 6. Post-deployment validation (run after the script completes).
-- ---------------------------------------------------------------------
-- SELECT COUNT(*) AS order_fact_rows,
--        COUNT(DISTINCT order_id) AS distinct_orders
-- FROM public.order_facts;
--
-- SELECT COUNT(*) AS customer_view_rows,
--        COUNT(DISTINCT customer_unique_id) AS distinct_customers
-- FROM public.customer360_view;
--
-- SELECT COUNT(*) AS rfm_rows,
--        COUNT(DISTINCT customer_unique_id) AS distinct_rfm_customers
-- FROM public.customer_rfm_view;
--
-- SELECT COUNT(*) FROM public.customer_clv_view;
-- SELECT COUNT(*) FROM public.seller_performance_view;
CREATE OR REPLACE VIEW public.seller_performance_view AS
WITH seller_order_metrics AS (
    SELECT
        oi.seller_id,
        oi.order_id,
        SUM(oi.price)::numeric(14,2) AS item_sales,
        MAX(f.review_score) AS review_score,
        CASE
            WHEN MAX(f.order_delivered_customer_date) >
                 MAX(f.order_estimated_delivery_date)
            THEN 1
            ELSE 0
        END AS is_late
    FROM public.order_items oi
    JOIN public.order_facts f
        ON f.order_id = oi.order_id
    WHERE f.is_revenue_order = TRUE
    GROUP BY oi.seller_id, oi.order_id
),
seller_summary AS (
    SELECT
        seller_id,
        COUNT(*) AS orders,
        SUM(item_sales)::numeric(14,2) AS item_sales,
        ROUND(AVG(review_score)::numeric, 2) AS avg_order_rating,
        ROUND(AVG(is_late::numeric) * 100, 2) AS late_delivery_pct
    FROM seller_order_metrics
    GROUP BY seller_id
)
SELECT
    s.seller_id,
    COALESCE(ss.orders, 0)::bigint AS orders,
    COALESCE(ss.item_sales, 0)::numeric(14,2) AS item_sales,
    ss.avg_order_rating,
    ss.late_delivery_pct,
    DENSE_RANK() OVER (
        ORDER BY COALESCE(ss.item_sales, 0) DESC
    ) AS sales_rank
FROM public.sellers s
LEFT JOIN seller_summary ss
    ON ss.seller_id = s.seller_id;