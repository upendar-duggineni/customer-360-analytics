from src.data_loader import load_data
from src.data_validation import validate_data
from src.data_cleaning import clean_data
from src.db_connection import engine
from src.postgres_loader import load_to_postgres


def main():

    print("=" * 60)
    print("CUSTOMER 360 ANALYTICS PLATFORM")
    print("=" * 60)

    print("\nLoading datasets...\n")

    # --------------------------------------------------
    # LOAD DATA
    # --------------------------------------------------

    (
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
        sellers,
        geolocation,
        category_translation
    ) = load_data()

    print("✅ Data Loaded Successfully.\n")


    # --------------------------------------------------
    # VALIDATE DATA
    # --------------------------------------------------

    validate_data(
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products
    )


    # --------------------------------------------------
    # CLEAN DATA
    # --------------------------------------------------

    (
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products
    ) = clean_data(
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products
    )


    # --------------------------------------------------
    # LOAD INTO POSTGRESQL
    # --------------------------------------------------

    load_to_postgres(
        engine,
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
        sellers,
        geolocation,
        category_translation
    )


    print("\n" + "=" * 60)
    print("🎉 ETL PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()