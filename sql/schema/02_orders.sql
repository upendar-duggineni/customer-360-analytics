DROP TABLE IF EXISTS products CASCADE;

CREATE TABLE products (

    product_id VARCHAR(50) PRIMARY KEY,

    product_category_name VARCHAR(100),

    product_name_lenght NUMERIC,

    product_description_lenght NUMERIC,

    product_photos_qty NUMERIC,

    product_weight_g NUMERIC,

    product_length_cm NUMERIC,

    product_height_cm NUMERIC,

    product_width_cm NUMERIC

);