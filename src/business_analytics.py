"""Reusable Customer 360 analytics for normalized business workspace datasets.

Metrics are calculated only when the required source fields exist. Historical
observations are distinguished from predictions: churn flags are inactivity
rules, and observed revenue is not represented as predictive lifetime value.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _empty():
    return pd.DataFrame()


def _as_date(values):
    return pd.to_datetime(values, errors="coerce", utc=True).dt.tz_convert(None)


def _score(series: pd.Series, ascending: bool):
    """Return stable 1-5 quantile-like scores, including small datasets."""
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.notna()
    result = pd.Series(index=series.index, dtype="float64")
    if valid.sum() == 0:
        return result
    ranks = numeric[valid].rank(method="average", pct=True, ascending=ascending)
    result.loc[valid] = np.ceil(ranks * 5).clip(1, 5)
    return result


def build_customer_360(tables: dict, churn_days: int = 90, as_of_date=None):
    """Build customer, RFM, cohort, trend and summary outputs from uploaded tables."""
    customers = tables.get("Customers", _empty()).copy()
    orders = tables.get("Orders", _empty()).copy()
    payments = tables.get("Payments", _empty()).copy()
    items = tables.get("Order items", _empty()).copy()

    result = {
        "summary": {},
        "customers": _empty(),
        "rfm": _empty(),
        "cohort": _empty(),
        "monthly": _empty(),
        "insights": [],
        "limitations": [],
    }

    if orders.empty or not {"order_id", "customer_id"}.issubset(orders.columns):
        result["limitations"].append("Upload an Orders dataset with order_id and customer_id to calculate customer-level analytics.")
        return result

    orders = orders.dropna(subset=["order_id", "customer_id"]).copy()
    orders["order_id"] = orders["order_id"].astype(str)
    orders["customer_id"] = orders["customer_id"].astype(str)
    duplicate_order_ids = int(orders["order_id"].duplicated(keep=False).sum())
    if duplicate_order_ids:
        result["limitations"].append(
            f"{duplicate_order_ids:,} order rows have duplicate order_id values; "
            "the first row per order_id is used for order-level customer metrics. "
            "Review the source Orders file."
        )
        orders = orders.drop_duplicates("order_id", keep="first").copy()
    if "order_purchase_timestamp" in orders:
        orders["order_purchase_timestamp"] = _as_date(orders["order_purchase_timestamp"])
    else:
        orders["order_purchase_timestamp"] = pd.NaT
        result["limitations"].append("Order dates are unavailable; recency, cohorts and monthly trends cannot be calculated.")

    # Establish one revenue value per order to prevent row multiplication when
    # joining order-level revenue to customers.
    order_revenue = None
    revenue_source = None
    if not payments.empty and {"order_id", "payment_value"}.issubset(payments.columns):
        pay = payments[["order_id", "payment_value"]].copy()
        pay["order_id"] = pay["order_id"].astype(str)
        pay["payment_value"] = pd.to_numeric(pay["payment_value"], errors="coerce")
        order_revenue = pay.groupby("order_id", as_index=False)["payment_value"].sum(min_count=1)
        order_revenue = order_revenue.rename(columns={"payment_value": "order_revenue"})
        revenue_source = "Payments"
    elif not payments.empty and {"order_id", "payment_amount"}.issubset(payments.columns):
        pay = payments[["order_id", "payment_amount"]].copy()
        pay["order_id"] = pay["order_id"].astype(str)
        pay["payment_amount"] = pd.to_numeric(pay["payment_amount"], errors="coerce")
        order_revenue = pay.groupby("order_id", as_index=False)["payment_amount"].sum(min_count=1)
        order_revenue = order_revenue.rename(columns={"payment_amount": "order_revenue"})
        revenue_source = "Payments"
    elif not orders.empty and {"order_id", "order_total"}.issubset(orders.columns):
        order_revenue = orders[["order_id", "order_total"]].copy()
        order_revenue["order_id"] = order_revenue["order_id"].astype(str)
        order_revenue["order_total"] = pd.to_numeric(order_revenue["order_total"], errors="coerce")
        order_revenue = order_revenue.rename(columns={"order_total": "order_revenue"})
        revenue_source = "Orders"
    elif not items.empty and {"order_id", "price"}.issubset(items.columns):
        line = items[["order_id", "price"]].copy()
        line["order_id"] = line["order_id"].astype(str)
        line["price"] = pd.to_numeric(line["price"], errors="coerce")
        order_revenue = line.groupby("order_id", as_index=False)["price"].sum(min_count=1)
        order_revenue = order_revenue.rename(columns={"price": "order_revenue"})
        revenue_source = "Order items"
    elif not items.empty and {"order_id", "unit_price"}.issubset(items.columns):
        line = items[["order_id", "unit_price"]].copy()
        line["order_id"] = line["order_id"].astype(str)
        line["unit_price"] = pd.to_numeric(line["unit_price"], errors="coerce")
        if "quantity" in items.columns:
            line["quantity"] = pd.to_numeric(items["quantity"], errors="coerce").fillna(1)
            line["line_revenue"] = line["unit_price"] * line["quantity"]
        else:
            line["line_revenue"] = line["unit_price"]
        order_revenue = line.groupby("order_id", as_index=False)["line_revenue"].sum(min_count=1)
        order_revenue = order_revenue.rename(columns={"line_revenue": "order_revenue"})
        revenue_source = "Order items"
    else:
        result["limitations"].append("Revenue-based metrics need Payments.payment_value or Order items.price.")

    if order_revenue is not None:
        orders = orders.merge(order_revenue, on="order_id", how="left", validate="many_to_one")
    else:
        orders["order_revenue"] = np.nan

    valid_dates = orders["order_purchase_timestamp"].dropna()
    snapshot = pd.Timestamp(as_of_date) if as_of_date is not None else (
        valid_dates.max() if not valid_dates.empty else pd.Timestamp.utcnow().tz_localize(None)
    )
    if getattr(snapshot, "tzinfo", None) is not None:
        snapshot = snapshot.tz_convert(None)

    grouped = orders.groupby("customer_id", dropna=True)
    customer_metrics = grouped.agg(
        frequency=("order_id", "nunique"),
        first_purchase=("order_purchase_timestamp", "min"),
        last_purchase=("order_purchase_timestamp", "max"),
    ).reset_index()
    if orders["order_revenue"].notna().any():
        customer_revenue = grouped["order_revenue"].sum(min_count=1).rename("observed_revenue")
        customer_metrics = customer_metrics.merge(
            customer_revenue, on="customer_id", how="left", validate="one_to_one"
        )
    else:
        customer_metrics["observed_revenue"] = np.nan
    customer_metrics["recency_days"] = (
        snapshot - customer_metrics["last_purchase"]
    ).dt.days
    customer_metrics["average_order_value"] = (
        customer_metrics["observed_revenue"] / customer_metrics["frequency"]
    )
    customer_metrics["is_repeat_customer"] = customer_metrics["frequency"] > 1
    customer_metrics["churn_status"] = np.where(
        customer_metrics["recency_days"].notna()
        & (customer_metrics["recency_days"] > int(churn_days)),
        "Inactive by rule",
        "Recently active / unknown",
    )

    # Attach customer attributes without multiplying customer records.
    if not customers.empty and "customer_id" in customers.columns:
        customer_attributes = customers.copy()
        customer_attributes["customer_id"] = customer_attributes["customer_id"].astype(str)
        customer_attributes = customer_attributes.drop_duplicates("customer_id", keep="last")
        extra = [c for c in ["customer_unique_id", "customer_name", "customer_email", "customer_phone", "customer_city", "customer_state", "customer_pincode"] if c in customer_attributes.columns]
        if extra:
            customer_metrics = customer_metrics.merge(
                customer_attributes[["customer_id"] + extra],
                on="customer_id",
                how="left",
                validate="one_to_one",
            )

    # RFM is calculated only if usable order dates and monetary data exist.
    rfm = customer_metrics[["customer_id", "recency_days", "frequency", "observed_revenue"]].copy()
    if rfm["recency_days"].notna().any() and rfm["observed_revenue"].notna().any():
        rfm["R_score"] = _score(rfm["recency_days"], ascending=False)
        rfm["F_score"] = _score(rfm["frequency"], ascending=True)
        rfm["M_score"] = _score(rfm["observed_revenue"], ascending=True)
        rfm["RFM_score"] = rfm[["R_score", "F_score", "M_score"]].sum(axis=1, min_count=3)
        rfm["segment"] = np.select(
            [
                (rfm["R_score"] >= 4) & (rfm["F_score"] >= 4) & (rfm["M_score"] >= 4),
                (rfm["R_score"] >= 3) & (rfm["F_score"] >= 3),
                (rfm["R_score"] <= 2) & (rfm["F_score"] >= 3),
                (rfm["R_score"] <= 2) & (rfm["F_score"] <= 2),
            ],
            ["Champions", "Loyal customers", "At risk", "Needs attention"],
            default="Potential / developing",
        )
        customer_metrics = customer_metrics.merge(
            rfm[["customer_id", "R_score", "F_score", "M_score", "RFM_score", "segment"]],
            on="customer_id",
            how="left",
            validate="one_to_one",
        )
    else:
        result["limitations"].append("RFM segmentation requires valid order dates and a supported revenue field.")

    # Cohorts use first observed order month and each subsequent order month.
    dated_orders = orders.dropna(subset=["order_purchase_timestamp"]).copy()
    cohort_table = _empty()
    monthly = _empty()
    if not dated_orders.empty:
        dated_orders["order_month"] = dated_orders["order_purchase_timestamp"].dt.to_period("M")
        first_month = dated_orders.groupby("customer_id")["order_month"].min().rename("cohort_month")
        dated_orders = dated_orders.join(first_month, on="customer_id")
        dated_orders["cohort_index"] = (
            (dated_orders["order_month"].dt.year - dated_orders["cohort_month"].dt.year) * 12
            + dated_orders["order_month"].dt.month
            - dated_orders["cohort_month"].dt.month
        )
        cohort_counts = dated_orders.groupby(["cohort_month", "cohort_index"])["customer_id"].nunique()
        cohort_sizes = dated_orders.groupby("cohort_month")["customer_id"].nunique()
        cohort_table = (cohort_counts / cohort_sizes).unstack().sort_index()
        cohort_table.index = cohort_table.index.astype(str)
        monthly = dated_orders.groupby("order_month").agg(
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
        ).reset_index()
        monthly["month"] = monthly["order_month"].astype(str)
        if order_revenue is not None:
            rev_orders = dated_orders[["order_id", "order_month"]].drop_duplicates().merge(
                order_revenue, on="order_id", how="left", validate="one_to_one"
            )
            revenue_monthly = rev_orders.groupby("order_month")["order_revenue"].sum(min_count=1)
            monthly["revenue"] = monthly["order_month"].map(revenue_monthly)
        monthly = monthly.drop(columns=["order_month"])

    total_customers = int(customer_metrics["customer_id"].nunique())
    total_orders = int(orders["order_id"].nunique())
    repeat_customers = int(customer_metrics["is_repeat_customer"].sum())
    revenue_total = customer_metrics["observed_revenue"].sum(min_count=1)
    result["summary"] = {
        "customers": total_customers,
        "orders": total_orders,
        "repeat_customers": repeat_customers,
        "repeat_rate": repeat_customers / total_customers if total_customers else np.nan,
        "revenue": revenue_total,
        "revenue_source": revenue_source,
        "average_order_value": revenue_total / total_orders if pd.notna(revenue_total) and total_orders else np.nan,
        "churn_rule_customers": int((customer_metrics["churn_status"] == "Inactive by rule").sum()),
        "churn_days": int(churn_days),
        "snapshot_date": snapshot,
    }

    if total_customers:
        repeat_rate = result["summary"]["repeat_rate"]
        result["insights"].append(
            f"{repeat_customers:,} of {total_customers:,} customers have placed more than one order ({repeat_rate:.1%})."
        )
    if pd.notna(revenue_total):
        result["insights"].append(
            f"Observed revenue totals {revenue_total:,.2f}, calculated from {revenue_source.lower()} data. Currency is not inferred."
        )
    if result["summary"]["churn_rule_customers"]:
        result["insights"].append(
            f"{result['summary']['churn_rule_customers']:,} customers have no recorded order within the last {int(churn_days)} days of the data snapshot. This is an inactivity rule, not a predictive churn model."
        )
    if not cohort_table.empty:
        result["insights"].append(
            "Cohort retention compares each cohort's active customers in later calendar months with its first-month customer count."
        )

    result["customers"] = customer_metrics.sort_values(
        ["observed_revenue", "frequency"], ascending=[False, False], na_position="last"
    )
    result["rfm"] = rfm
    result["cohort"] = cohort_table
    result["monthly"] = monthly
    return result
