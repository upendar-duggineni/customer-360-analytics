DROP TABLE IF EXISTS geolocation CASCADE;

CREATE TABLE geolocation (

    geolocation_zip_code_prefix INT,

    geolocation_lat NUMERIC,

    geolocation_lng NUMERIC,

    geolocation_city VARCHAR(100),

    geolocation_state VARCHAR(5)

);