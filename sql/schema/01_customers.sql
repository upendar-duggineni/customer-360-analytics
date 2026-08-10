DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (

    customer_id VARCHAR(50) PRIMARY KEY,

    customer_unique_id VARCHAR(50) NOT NULL,

    customer_zip_code_prefix INT,

    customer_city VARCHAR(100),

    customer_state VARCHAR(5)

);