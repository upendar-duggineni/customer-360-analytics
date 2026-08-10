DROP TABLE IF EXISTS order_items CASCADE;

CREATE TABLE order_items (

    order_id VARCHAR(50),

    order_item_id INT,

    product_id VARCHAR(50),

    seller_id VARCHAR(50),

    shipping_limit_date TIMESTAMP,

    price NUMERIC,

    freight_value NUMERIC,

    PRIMARY KEY(order_id, order_item_id),

    CONSTRAINT fk_order
    FOREIGN KEY(order_id)
    REFERENCES orders(order_id),

    CONSTRAINT fk_product
    FOREIGN KEY(product_id)
    REFERENCES products(product_id),

    CONSTRAINT fk_seller
    FOREIGN KEY(seller_id)
    REFERENCES sellers(seller_id)

);