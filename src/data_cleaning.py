import pandas as pd


def clean_data(customers,
               orders,
               order_items,
               payments,
               reviews,
               products):

    print("\nCleaning Data...\n")

    # =====================================================
    # Remove Duplicate Records
    # =====================================================

    customers = customers.drop_duplicates()

    orders = orders.drop_duplicates()

    order_items = order_items.drop_duplicates()

    payments = payments.drop_duplicates()

    reviews = reviews.drop_duplicates()

    products = products.drop_duplicates()

    # =====================================================
    # Convert Date Columns
    # =====================================================

    order_date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]

    for column in order_date_columns:
        orders[column] = pd.to_datetime(
            orders[column],
            errors="coerce"
        )

    order_items["shipping_limit_date"] = pd.to_datetime(
        order_items["shipping_limit_date"],
        errors="coerce"
    )

    reviews["review_creation_date"] = pd.to_datetime(
        reviews["review_creation_date"],
        errors="coerce"
    )

    reviews["review_answer_timestamp"] = pd.to_datetime(
        reviews["review_answer_timestamp"],
        errors="coerce"
    )

    # =====================================================
    # Handle Missing Values - Products
    # =====================================================

    products["product_category_name"] = products[
        "product_category_name"
    ].fillna("Unknown")

    numeric_columns = [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm"
    ]

    for column in numeric_columns:
        products[column] = products[column].fillna(
            products[column].median()
        )

    # =====================================================
    # Handle Missing Values - Reviews
    # =====================================================

    reviews["review_comment_title"] = reviews[
        "review_comment_title"
    ].fillna("No Title")

    reviews["review_comment_message"] = reviews[
        "review_comment_message"
    ].fillna("No Review")

    # =====================================================
    # Convert Numeric Columns
    # =====================================================

    payments["payment_value"] = payments["payment_value"].astype(float)

    order_items["price"] = order_items["price"].astype(float)

    order_items["freight_value"] = order_items["freight_value"].astype(float)

    print("✅ Data Cleaning Completed Successfully.\n")

    return (
        customers,
        orders,
        order_items,
        payments,
        reviews,
        products
    )