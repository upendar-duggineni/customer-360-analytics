DROP TABLE IF EXISTS reviews CASCADE;

CREATE TABLE reviews (

    review_id VARCHAR(50),

    order_id VARCHAR(50),

    review_score INT,

    review_comment_title TEXT,

    review_comment_message TEXT,

    review_creation_date TIMESTAMP,

    review_answer_timestamp TIMESTAMP,

    PRIMARY KEY(review_id, order_id),

    CONSTRAINT fk_review_order
    FOREIGN KEY(order_id)
    REFERENCES orders(order_id)

);