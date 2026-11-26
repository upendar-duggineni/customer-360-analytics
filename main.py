
from src.data_loader import load_data
from src.data_validation import validate_data
from src.data_cleaning import clean_data
from src.db_connection import engine
from src.postgres_loader import load_to_postgres


def main():
    print("=" * 65)
    print("CUSTOMER 360 ANALYTICS PLATFORM")
    print("=" * 65)

    # --------------------------------------------------
    # 1. LOAD DATA
    # --------------------------------------------------

    print("\n[1/5] Loading datasets...\n")

    (
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
        sellers,
        geolocation,
        category_translation,
    ) = load_data()

    print("All nine datasets loaded successfully.")

    # --------------------------------------------------
    # 2. VALIDATE RAW DATA
    # --------------------------------------------------

    print("\n[2/5] Validating raw datasets...\n")

    validate_data(
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
        sellers,
        geolocation,
        category_translation,
        stage="before cleaning",
    )

    # --------------------------------------------------
    # 3. CLEAN DATA
    # --------------------------------------------------

    print("\n[3/5] Cleaning datasets...\n")

    (
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
    ) = clean_data(
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
    )

    # --------------------------------------------------
    # 4. VALIDATE CLEANED DATA
    # --------------------------------------------------

    print("\n[4/5] Validating cleaned datasets...\n")

    validate_data(
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products,
        sellers,
        geolocation,
        category_translation,
        stage="after cleaning",
    )

    # --------------------------------------------------
    # 5. LOAD INTO POSTGRESQL
    # --------------------------------------------------

    print("\n[5/5] Loading data into PostgreSQL...\n")

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
        category_translation,
    )

    print("\n" + "=" * 65)
    print("ETL PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 65)


if __name__ == "__main__":
    main()
