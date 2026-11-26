"""Deterministic, workspace-scoped analytics tools for the AI assistant."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from src.business_analytics import build_customer_360
from src.customer_360_detail import build_customer_360_detail


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _records(frame: pd.DataFrame, limit: int = 20) -> list[dict]:
    if frame is None or frame.empty:
        return []
    return [
        {str(k): _json_safe(v) for k, v in row.items()}
        for row in frame.head(limit).to_dict(orient="records")
    ]


def _number(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in frame.columns), None)


def _available(tables: dict, required: list[str]) -> dict:
    missing = [name for name in required if name not in tables or tables[name].empty]
    return {"available": not missing, "missing_datasets": missing}


def get_business_overview(tables: dict) -> dict:
    """Return workspace coverage, core KPIs, and known data limitations."""
    analytics = build_customer_360(tables, churn_days=90)
    relationship_datasets = {
        name: {"rows": int(len(frame)), "columns": list(frame.columns)}
        for name, frame in tables.items()
    }
    summary = analytics.get("summary", {})
    return {
        "datasets": relationship_datasets,
        "kpis": {
            key: _json_safe(summary.get(key))
            for key in [
                "customers", "orders", "repeat_customers", "repeat_rate",
                "revenue", "revenue_source", "average_order_value",
                "churn_rule_customers", "churn_days", "snapshot_date",
                "customer_only",
            ]
            if key in summary
        },
        "insights": analytics.get("insights", [])[:10],
        "limitations": analytics.get("limitations", [])[:15],
        "definitions": {
            "revenue": "Historical observed revenue from the analytics engine's selected source; currency is not inferred.",
            "inactivity": "A 90-day recency rule, not a predictive churn model.",
            "customer_lifetime_value": "Not predicted by this tool.",
        },
    }


def get_top_customers(tables: dict, limit: int = 10) -> dict:
    """Return top customers ranked by historical observed revenue."""
    if not 1 <= int(limit) <= 25:
        return {"error": "limit must be between 1 and 25"}
    analytics = build_customer_360(tables, churn_days=90)
    frame = analytics.get("customers", pd.DataFrame())
    if frame.empty or "observed_revenue" not in frame.columns:
        return {"available": False, "reason": "Customer revenue is unavailable. Upload compatible Orders and Payments or Order items data."}
    columns = [c for c in [
        "customer_id", "frequency", "observed_revenue", "first_purchase",
        "last_purchase", "is_repeat_customer", "churn_status", "segment"
    ] if c in frame.columns]
    return {
        "available": True,
        "ranking_basis": "observed_revenue",
        "currency": "Not inferred from uploaded data",
        "customers": _records(frame.sort_values("observed_revenue", ascending=False)[columns], int(limit)),
    }


def lookup_customer(tables: dict, customer_id: str) -> dict:
    """Look up one customer by exact canonical customer_id, without exposing contact PII."""
    clean_id = str(customer_id).strip()
    if not clean_id or len(clean_id) > 128:
        return {"error": "Provide a valid customer ID (maximum 128 characters)."}
    if "Customers" not in tables:
        return {"available": False, "reason": "Customers dataset has not been uploaded."}
    detail = build_customer_360_detail(tables, clean_id)
    if detail["customer"].empty:
        return {"available": True, "found": False, "customer_id": clean_id}
    profile = detail["customer"].iloc[0]
    safe_profile = {
        key: _json_safe(profile[key])
        for key in ["customer_id", "customer_city", "customer_state", "customer_country", "customer_pincode", "signup_date"]
        if key in detail["customer"].columns
    }
    orders = detail["orders"]
    order_cols = [c for c in ["order_id", "order_status", "order_purchase_timestamp"] if c in orders.columns]
    return {
        "available": True,
        "found": True,
        "profile": safe_profile,
        "order_count": int(len(orders)),
        "orders": _records(orders[order_cols], 20),
        "order_items": int(len(detail["order_items"])),
        "payment_rows": int(len(detail["payments"])),
        "review_rows": int(len(detail["reviews"])),
        "recorded_payment_total": _json_safe(detail["summary"]["recorded_payment_total"]),
        "note": "Email and phone fields are intentionally excluded from AI context.",
    }


def get_monthly_trends(tables: dict, limit: int = 24) -> dict:
    """Return monthly order/customer/revenue trend rows from the analytics engine."""
    if not 1 <= int(limit) <= 60:
        return {"error": "limit must be between 1 and 60"}
    analytics = build_customer_360(tables, churn_days=90)
    monthly = analytics.get("monthly", pd.DataFrame())
    if monthly.empty:
        return {"available": False, "reason": "Monthly trends require compatible order dates and customer IDs."}
    return {"available": True, "trends": _records(monthly.tail(int(limit)), int(limit))}


def get_product_performance(tables: dict, limit: int = 10) -> dict:
    """Summarize product-category order lines and recorded item value."""
    if not 1 <= int(limit) <= 25:
        return {"error": "limit must be between 1 and 25"}
    items = tables.get("Order items", pd.DataFrame())
    products = tables.get("Products", pd.DataFrame())
    if items.empty:
        return {"available": False, "reason": "Order items dataset has not been uploaded."}
    if "product_id" not in items.columns or "product_id" not in products.columns:
        return {"available": False, "reason": "Map product_id in both Order items and Products to enable category analysis."}
    category_col = _number(products, ["product_category", "product_category_name"])
    if not category_col:
        return {"available": False, "reason": "Product category is not mapped in Products."}
    lookup = products[["product_id", category_col]].copy()
    lookup["_key"] = lookup["product_id"].astype("string").str.strip()
    duplicate = lookup["_key"].duplicated(keep=False)
    duplicate_keys = int(lookup.loc[duplicate, "_key"].nunique())
    lookup = lookup.loc[~duplicate].drop(columns=["product_id"]).rename(columns={category_col: "category"})
    data = items.copy()
    data["_key"] = data["product_id"].astype("string").str.strip()
    data = data.merge(lookup, on="_key", how="left", validate="many_to_one")
    data["category"] = data["category"].fillna("Unmatched / unknown")
    amount_col = _number(data, ["unit_price", "price"])
    grouped = data.groupby("category", dropna=False).agg(order_lines=("product_id", "size"))
    if amount_col:
        data["_amount"] = pd.to_numeric(data[amount_col], errors="coerce")
        grouped["recorded_item_value"] = data.groupby("category")["_amount"].sum(min_count=1)
    grouped = grouped.reset_index().sort_values("order_lines", ascending=False).head(int(limit))
    return {
        "available": True,
        "categories": _records(grouped, int(limit)),
        "duplicate_product_keys_excluded": duplicate_keys,
        "note": "Order-line counts are not unit counts. Item value is not necessarily net revenue and currency is not inferred.",
    }


def get_payment_analysis(tables: dict, limit: int = 10) -> dict:
    """Summarize payment amounts by mapped payment method."""
    if not 1 <= int(limit) <= 25:
        return {"error": "limit must be between 1 and 25"}
    payments = tables.get("Payments", pd.DataFrame())
    if payments.empty:
        return {"available": False, "reason": "Payments dataset has not been uploaded."}
    amount_col = _number(payments, ["payment_amount", "payment_value"])
    method_col = _number(payments, ["payment_method", "payment_type"])
    if not amount_col:
        return {"available": False, "reason": "Payment amount is not mapped."}
    if not method_col:
        values = pd.to_numeric(payments[amount_col], errors="coerce")
        return {"available": True, "recorded_payment_total": _json_safe(values.sum(min_count=1)), "payment_rows": int(values.notna().sum()), "note": "Payment method is not mapped; no method comparison is possible. Currency is not inferred."}
    work = payments[[method_col, amount_col]].copy()
    work[amount_col] = pd.to_numeric(work[amount_col], errors="coerce")
    grouped = work.groupby(method_col, dropna=False).agg(
        payment_rows=(amount_col, "count"),
        recorded_payment_total=(amount_col, lambda x: x.sum(min_count=1)),
    ).reset_index().sort_values("recorded_payment_total", ascending=False).head(int(limit))
    return {
        "available": True,
        "payment_methods": _records(grouped, int(limit)),
        "note": "Recorded payment totals; currency is not inferred and installment rows may make payment rows differ from order counts.",
    }


TOOL_FUNCTIONS = {
    "get_business_overview": get_business_overview,
    "get_top_customers": get_top_customers,
    "lookup_customer": lookup_customer,
    "get_monthly_trends": get_monthly_trends,
    "get_product_performance": get_product_performance,
    "get_payment_analysis": get_payment_analysis,
}

TOOL_SCHEMAS = [
    {"type": "function", "name": "get_business_overview", "description": "Get available datasets, core KPIs, evidence-based insights, metric definitions and data limitations for the active workspace.", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_top_customers", "description": "Rank customers by historical observed revenue. Use only when the user asks for top or highest-value customers.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 25}}, "required": ["limit"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "lookup_customer", "description": "Look up a customer by exact customer ID and return a minimized profile and related order/payment/review counts.", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string", "maxLength": 128}}, "required": ["customer_id"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_monthly_trends", "description": "Get monthly orders, customers and observed revenue trends.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 60}}, "required": ["limit"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_product_performance", "description": "Compare product categories by order-line count and recorded item value.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 25}}, "required": ["limit"], "additionalProperties": False}, "strict": True},
    {"type": "function", "name": "get_payment_analysis", "description": "Analyze recorded payments and mapped payment methods.", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 25}}, "required": ["limit"], "additionalProperties": False}, "strict": True},
]
