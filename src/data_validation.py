
def validate_data(
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
):
    """
    Validate all nine Olist datasets.

    Raises ValueError when structural, key, or referential-integrity
    checks fail. Known business-data anomalies are not automatically
    treated as fatal errors.
    """

    datasets = {
        "customers": customers,
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
        "reviews": reviews,
        "products": products,
        "sellers": sellers,
        "geolocation": geolocation,
        "category_translation": category_translation,
    }

    required_columns = {
        "customers": {
            "customer_id", "customer_unique_id",
            "customer_zip_code_prefix", "customer_city",
            "customer_state",
        },
        "orders": {
            "order_id", "customer_id", "order_status",
            "order_purchase_timestamp",
        },
        "order_items": {
            "order_id", "order_item_id", "product_id",
            "seller_id", "price", "freight_value",
        },
        "payments": {
            "order_id", "payment_sequential",
            "payment_type", "payment_value",
        },
        "reviews": {
            "review_id", "order_id", "review_score",
        },
        "products": {
            "product_id", "product_category_name",
        },
        "sellers": {
            "seller_id", "seller_zip_code_prefix",
            "seller_city", "seller_state",
        },
        "geolocation": {
            "geolocation_zip_code_prefix",
            "geolocation_lat", "geolocation_lng",
            "geolocation_city", "geolocation_state",
        },
        "category_translation": {
            "product_category_name",
            "product_category_name_english",
        },
    }

    # Logical keys in the source datasets.
    key_columns = {
        "customers": ["customer_id"],
        "orders": ["order_id"],
        "order_items": ["order_id", "order_item_id"],
        "payments": ["order_id", "payment_sequential"],
        "reviews": ["review_id", "order_id"],
        "products": ["product_id"],
        "sellers": ["seller_id"],
        "category_translation": ["product_category_name"],
    }

    errors = []

    print("\n" + "=" * 65)
    print(f"DATA VALIDATION — {stage.upper()}")
    print("=" * 65)

    # 1. Check required columns, empty datasets and key integrity.
    for name, dataframe in datasets.items():
        print(f"\n{name.upper()}")
        print(f"Rows: {len(dataframe):,}")
        print(f"Columns: {len(dataframe.columns)}")

        missing_columns = (
            required_columns[name] - set(dataframe.columns)
        )

        if missing_columns:
            errors.append(
                f"{name}: missing columns "
                f"{sorted(missing_columns)}"
            )
            continue

        if dataframe.empty:
            errors.append(f"{name}: dataset is empty")
            continue

        print(
            "Missing values in required columns:",
            int(
                dataframe[
                    list(required_columns[name])
                ].isnull().sum().sum()
            ),
        )

        if name in key_columns:
            keys = key_columns[name]

            null_key_rows = dataframe[keys].isnull().any(axis=1).sum()

            duplicate_rows = dataframe.duplicated(
                subset=keys
            ).sum()

            if null_key_rows:
                errors.append(
                    f"{name}: {null_key_rows} rows have null key values"
                )

            if duplicate_rows:
                errors.append(
                    f"{name}: {duplicate_rows} duplicate key rows "
                    f"for {keys}"
                )

    # 2. Check foreign-key relationships only if the relevant
    #    datasets contain their required columns.
    relationships = [
        (
            "orders.customer_id",
            orders, "customer_id",
            customers, "customer_id",
        ),
        (
            "order_items.order_id",
            order_items, "order_id",
            orders, "order_id",
        ),
        (
            "order_items.product_id",
            order_items, "product_id",
            products, "product_id",
        ),
        (
            "order_items.seller_id",
            order_items, "seller_id",
            sellers, "seller_id",
        ),
        (
            "payments.order_id",
            payments, "order_id",
            orders, "order_id",
        ),
        (
            "reviews.order_id",
            reviews, "order_id",
            orders, "order_id",
        ),
    ]

    print("\nREFERENTIAL INTEGRITY")

    for label, child, child_col, parent, parent_col in relationships:
        if (
            child_col not in child.columns
            or parent_col not in parent.columns
        ):
            continue

        valid_parent_values = set(
            parent[parent_col].dropna()
        )

        orphan_mask = (
            child[child_col].notna()
            & ~child[child_col].isin(valid_parent_values)
        )

        orphan_count = int(orphan_mask.sum())

        print(f"{label}: {orphan_count} orphan rows")

        if orphan_count:
            errors.append(
                f"{label}: {orphan_count} orphan references"
            )

    # 3. Report business-data anomalies without automatically
    #    rejecting the source data.
    if "payment_value" in payments.columns:
        zero_payments = int(
            (payments["payment_value"] == 0).sum()
        )
        negative_payments = int(
            (payments["payment_value"] < 0).sum()
        )

        print("\nBUSINESS-DATA WARNINGS")
        print(f"Zero-value payment records: {zero_payments}")
        print(f"Negative payment records: {negative_payments}")

    if errors:
        print("\nVALIDATION FAILED")

        for error in errors:
            print(f"- {error}")

        raise ValueError(
            f"Data validation failed at stage: {stage}"
        )

    print("\nVALIDATION PASSED")
    return True
