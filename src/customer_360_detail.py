"""Relationship-safe, drill-down Customer 360 records for a selected customer."""
from __future__ import annotations

import pandas as pd


def _frame(tables: dict, name: str) -> pd.DataFrame:
    value = tables.get(name)
    return value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame()


def _key(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def build_customer_360_detail(tables: dict, customer_id: str) -> dict:
    """Return separate one-to-many detail tables without multiplying records.

    Product attributes are added only through a unique product lookup. Duplicate
    product keys are reported and excluded from enrichment rather than causing
    item-row multiplication. Input frames are never mutated.
    """
    selected_id = str(customer_id).strip()
    customers = _frame(tables, "Customers")
    orders_source = _frame(tables, "Orders")
    items_source = _frame(tables, "Order items")
    products_source = _frame(tables, "Products")
    payments_source = _frame(tables, "Payments")
    reviews_source = _frame(tables, "Reviews")

    customer = pd.DataFrame()
    if "customer_id" in customers.columns:
        customer = customers.loc[_key(customers["customer_id"]).eq(selected_id)].copy()

    orders = pd.DataFrame()
    if {"customer_id", "order_id"}.issubset(orders_source.columns):
        orders = orders_source.loc[_key(orders_source["customer_id"]).eq(selected_id)].copy()
        orders["_order_key"] = _key(orders["order_id"])
        orders = orders.loc[orders["_order_key"].notna() & orders["_order_key"].ne("")]
        order_keys = set(orders["_order_key"].tolist())
    else:
        order_keys = set()

    order_items = pd.DataFrame()
    duplicate_product_keys = 0
    if "order_id" in items_source.columns and order_keys:
        order_items = items_source.loc[_key(items_source["order_id"]).isin(order_keys)].copy()
        if "product_id" in order_items.columns and "product_id" in products_source.columns:
            product_lookup = products_source.copy()
            product_lookup["_product_key"] = _key(product_lookup["product_id"])
            valid_product = product_lookup["_product_key"].notna() & product_lookup["_product_key"].ne("")
            duplicate_mask = valid_product & product_lookup["_product_key"].duplicated(keep=False)
            duplicate_product_keys = int(product_lookup.loc[duplicate_mask, "_product_key"].nunique())
            product_lookup = product_lookup.loc[valid_product & ~duplicate_mask].drop_duplicates("_product_key")
            product_columns = [
                column for column in
                ["product_name", "product_category", "brand"]
                if column in product_lookup.columns
            ]
            if product_columns:
                product_lookup = product_lookup[["_product_key"] + product_columns]
                order_items["_product_key"] = _key(order_items["product_id"])
                order_items = order_items.merge(
                    product_lookup, on="_product_key", how="left", validate="many_to_one"
                ).drop(columns=["_product_key"])

    def related(frame: pd.DataFrame) -> pd.DataFrame:
        if "order_id" not in frame.columns or not order_keys:
            return pd.DataFrame(columns=frame.columns)
        return frame.loc[_key(frame["order_id"]).isin(order_keys)].copy()

    payments = related(payments_source)
    reviews = related(reviews_source)

    payment_amount_col = next(
        (column for column in ["payment_amount", "payment_value"] if column in payments.columns),
        None,
    )
    payment_total = (
        pd.to_numeric(payments[payment_amount_col], errors="coerce").sum(min_count=1)
        if payment_amount_col else None
    )

    return {
        "customer": customer,
        "orders": orders.drop(columns=["_order_key"], errors="ignore"),
        "order_items": order_items,
        "payments": payments,
        "reviews": reviews,
        "summary": {
            "customer_id": selected_id,
            "orders": len(orders),
            "order_items": len(order_items),
            "payments": len(payments),
            "reviews": len(reviews),
            "recorded_payment_total": payment_total,
            "duplicate_product_keys_excluded": duplicate_product_keys,
        },
    }
