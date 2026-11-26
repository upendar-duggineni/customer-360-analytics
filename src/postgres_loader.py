
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
    """Refresh all nine PostgreSQL tables atomically."""

    datasets = {
        "customers": customers,
        "products": products,
        "sellers": sellers,
        "orders": orders,
        "payments": payments,
        "reviews": reviews,
        "order_items": order_items,
        "geolocation": geolocation,
        "product_category_name_translation": category_translation,
    }

    print("\nStarting PostgreSQL full refresh...\n")

    # One transaction covers truncation, insertion and verification.
    with engine.begin() as conn:

        # Explicitly include every table involved in the audited
        # foreign-key relationships. No CASCADE or identity reset.
        conn.execute(text("""
            TRUNCATE TABLE
                order_items,
                reviews,
                payments,
                orders,
                products,
                sellers,
                customers,
                geolocation,
                product_category_name_translation;
        """))

        for table_name, dataframe in datasets.items():

            dataframe.to_sql(
                name=table_name,
                con=conn,
                if_exists="append",
                index=False,
                chunksize=10000,
            )

            print(f"Loaded {table_name}: {len(dataframe):,} rows")

        print("\nVerifying database row counts...\n")

        for table_name, dataframe in datasets.items():

            actual_count = conn.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}"')
            ).scalar_one()

            expected_count = len(dataframe)

            print(
                f"{table_name}: "
                f"expected={expected_count:,}, "
                f"actual={actual_count:,}"
            )

            if actual_count != expected_count:
                raise RuntimeError(
                    f"Row count mismatch in {table_name}"
                )

    print("\nPostgreSQL refresh committed successfully.")
