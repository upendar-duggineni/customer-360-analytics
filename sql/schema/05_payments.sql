DROP TABLE IF EXISTS payments CASCADE;

CREATE TABLE payments (

    payment_id SERIAL PRIMARY KEY,

    order_id VARCHAR(50),

    payment_sequential INT,

    payment_type VARCHAR(50),

    payment_installments INT,

    payment_value NUMERIC,

    CONSTRAINT fk_payment_order
    FOREIGN KEY(order_id)
    REFERENCES orders(order_id)

);