"""File ingestion helpers for the business workspace prototype.

Uploaded files are normalized in memory. This module never writes business
uploads into the Olist database or to a shared filesystem.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

import pandas as pd


TABLE_FIELDS = {
    "Customers": {
        "required": ["customer_id"],
        "optional": ["customer_unique_id", "customer_city", "customer_state"],
    },
    "Orders": {
        "required": ["order_id", "customer_id", "order_purchase_timestamp"],
        "optional": ["order_status"],
    },
    "Order items": {
        "required": ["order_id", "product_id"],
        "optional": ["price", "freight_value", "seller_id"],
    },
    "Products": {
        "required": ["product_id"],
        "optional": ["product_category_name"],
    },
    "Payments": {
        "required": ["order_id", "payment_value"],
        "optional": ["payment_type", "payment_installments"],
    },
}

ALIASES = {
    "customer_id": ["customer id", "customerid", "cust id", "cust_id", "client id", "client_number"],
    "customer_unique_id": ["customer unique id", "customer_unique_id", "unique customer id"],
    "customer_city": ["customer city", "city", "town"],
    "customer_state": ["customer state", "state", "province", "region"],
    "order_id": ["order id", "orderid", "order_no", "order number", "transaction id", "transaction_id"],
    "order_purchase_timestamp": ["order purchase timestamp", "purchase date", "purchase_date", "order date", "order_date", "created_at", "created date"],
    "order_status": ["order status", "status", "fulfilment status", "fulfillment status"],
    "product_id": ["product id", "productid", "sku", "item id", "item_id"],
    "price": ["price", "item price", "unit price", "sale price"],
    "freight_value": ["freight value", "shipping", "shipping cost", "delivery charge"],
    "seller_id": ["seller id", "sellerid", "merchant id"],
    "product_category_name": ["product category name", "category", "product category", "category_name"],
    "payment_value": ["payment value", "amount", "total", "total amount", "net amount", "net_amount", "total_price"],
    "payment_type": ["payment type", "payment method", "method"],
    "payment_installments": ["payment installments", "installments", "installment_count"],
}


def normalize_header(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Read a CSV or Excel upload without persisting it to disk."""
    suffix = Path(uploaded_file.name).suffix.lower()
    payload = BytesIO(uploaded_file.getvalue())

    if suffix == ".csv":
        try:
            return pd.read_csv(payload)
        except UnicodeDecodeError:
            payload.seek(0)
            return pd.read_csv(payload, encoding="latin-1")
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(payload, engine="openpyxl")
    if suffix == ".xls":
        raise ValueError("Legacy .xls files are not supported. Please save as .xlsx or .csv.")
    raise ValueError("Unsupported file type. Upload a .csv or .xlsx file.")


def suggest_mapping(columns, fields):
    """Return canonical field -> source column suggestions."""
    normalized = {normalize_header(column): column for column in columns}
    suggestions = {}
    for field in fields:
        candidates = [field.replace("_", " ")] + ALIASES.get(field, [])
        match = next(
            (normalized[normalize_header(candidate)]
             for candidate in candidates
             if normalize_header(candidate) in normalized),
            None,
        )
        suggestions[field] = match
    return suggestions


def normalize_dataframe(dataframe, mapping, table_name):
    """Rename mapped source columns to the platform's canonical names."""
    selected = {
        source: canonical
        for canonical, source in mapping.items()
        if source and source in dataframe.columns
    }
    result = dataframe[list(selected)].rename(columns=selected).copy()

    for field in TABLE_FIELDS[table_name]["required"]:
        if field not in result.columns:
            raise ValueError(f"Required field '{field}' has not been mapped.")

    # Normalize common data types without silently filling business values.
    if "order_purchase_timestamp" in result.columns:
        result["order_purchase_timestamp"] = pd.to_datetime(
            result["order_purchase_timestamp"], errors="coerce"
        )
    for field in ["price", "freight_value", "payment_value"]:
        if field in result.columns:
            result[field] = pd.to_numeric(result[field], errors="coerce")
    for field in ["customer_id", "customer_unique_id", "order_id", "product_id", "seller_id"]:
        if field in result.columns:
            result[field] = result[field].astype("string").str.strip()

    return result


def validate_dataframe(dataframe, table_name):
    """Return human-readable quality checks; errors block saving."""
    required = TABLE_FIELDS[table_name]["required"]
    issues = []
    warnings = []

    missing_fields = [field for field in required if field not in dataframe.columns]
    if missing_fields:
        issues.append("Missing required fields: " + ", ".join(missing_fields))
        return {"errors": issues, "warnings": warnings, "rows": len(dataframe)}

    for field in required:
        null_count = int(dataframe[field].isna().sum())
        if null_count:
            issues.append(f"{field}: {null_count:,} missing or invalid values")

    key_fields = {
        "Customers": ["customer_id"],
        "Orders": ["order_id"],
        "Order items": [],
        "Products": ["product_id"],
        "Payments": [],
    }[table_name]
    for field in key_fields:
        duplicate_count = int(dataframe[field].duplicated(keep=False).sum())
        if duplicate_count:
            warnings.append(f"{field}: {duplicate_count:,} rows participate in duplicate keys")

    duplicate_rows = int(dataframe.duplicated().sum())
    if duplicate_rows:
        warnings.append(f"{duplicate_rows:,} completely duplicated rows")

    if dataframe.empty:
        issues.append("The uploaded file contains no data rows.")

    return {
        "errors": issues,
        "warnings": warnings,
        "rows": len(dataframe),
        "columns": len(dataframe.columns),
        "duplicate_rows": duplicate_rows,
    }


def cross_table_checks(tables):
    """Return non-blocking relationship checks when both sides are available."""
    checks = []
    if "Orders" in tables and "Customers" in tables:
        orders = tables["Orders"]
        customers = tables["Customers"]
        if "customer_id" in orders and "customer_id" in customers:
            known = set(customers["customer_id"].dropna().astype(str))
            orphan = int((~orders["customer_id"].astype(str).isin(known)).sum())
            checks.append(("Orders → Customers", orphan, "orphan order customer references"))

    if "Order items" in tables and "Orders" in tables:
        items = tables["Order items"]
        orders = tables["Orders"]
        known = set(orders["order_id"].dropna().astype(str))
        orphan = int((~items["order_id"].astype(str).isin(known)).sum())
        checks.append(("Order items → Orders", orphan, "orphan order-item references"))

    if "Payments" in tables and "Orders" in tables:
        payments = tables["Payments"]
        orders = tables["Orders"]
        known = set(orders["order_id"].dropna().astype(str))
        orphan = int((~payments["order_id"].astype(str).isin(known)).sum())
        checks.append(("Payments → Orders", orphan, "orphan payment references"))

    return checks
