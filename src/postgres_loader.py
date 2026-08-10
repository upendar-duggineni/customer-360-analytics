from sqlalchemy import text


def load_to_postgres(
    engine,
    customers,
    orders,
    order_items,
    payments,
    reviews,
    products,
    sellers,
    geolocation,
    category_translation,
):

    print("\nLoading data into PostgreSQL...\n")

    # --------------------------------------------------
    # EMPTY EXISTING TABLES
    # --------------------------------------------------

    with engine.begin() as conn:

        conn.execute(text("TRUNCATE TABLE order_items CASCADE;"))
        conn.execute(text("TRUNCATE TABLE reviews CASCADE;"))
        conn.execute(text("TRUNCATE TABLE payments CASCADE;"))
        conn.execute(text("TRUNCATE TABLE orders CASCADE;"))
        conn.execute(text("TRUNCATE TABLE sellers CASCADE;"))
        conn.execute(text("TRUNCATE TABLE products CASCADE;"))
        conn.execute(text("TRUNCATE TABLE customers CASCADE;"))
        conn.execute(text("TRUNCATE TABLE geolocation CASCADE;"))

    # --------------------------------------------------
    # CUSTOMERS
    # --------------------------------------------------

    customers.to_sql(
        "customers",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Customers : {len(customers)}")

    # --------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------
    # IMPORTANT:
    # Keep the original Olist column names:
    # product_name_lenght
    # product_description_lenght

    products.to_sql(
        "products",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Products : {len(products)}")

    # --------------------------------------------------
    # SELLERS
    # --------------------------------------------------

    sellers.to_sql(
        "sellers",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Sellers : {len(sellers)}")

    # --------------------------------------------------
    # ORDERS
    # --------------------------------------------------

    orders.to_sql(
        "orders",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Orders : {len(orders)}")

    # --------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------

    payments.to_sql(
        "payments",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Payments : {len(payments)}")

    # --------------------------------------------------
    # REVIEWS
    # --------------------------------------------------

    reviews.to_sql(
        "reviews",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Reviews : {len(reviews)}")

    # --------------------------------------------------
    # ORDER ITEMS
    # --------------------------------------------------

    order_items.to_sql(
        "order_items",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Order Items : {len(order_items)}")

    # --------------------------------------------------
    # GEOLOCATION
    # --------------------------------------------------

    geolocation.to_sql(
        "geolocation",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✅ Geolocation : {len(geolocation)}")

    # --------------------------------------------------
    # PRODUCT CATEGORY TRANSLATION
    # --------------------------------------------------

    category_translation.to_sql(
        "product_category_name_translation",
        engine,
        if_exists="replace",
        index=False
    )

    print(
        f"✅ Category Translation : "
        f"{len(category_translation)}"
    )

    print("\n🎉 Data Loaded Successfully!")