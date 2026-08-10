DROP TABLE IF EXISTS sellers CASCADE;

CREATE TABLE sellers (

    seller_id VARCHAR(50) PRIMARY KEY,

    seller_zip_code_prefix INT,

    seller_city VARCHAR(100),

    seller_state VARCHAR(10)

);