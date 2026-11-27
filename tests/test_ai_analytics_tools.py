import pandas as pd

from src.ai_assistant.analytics_tools import (
    get_business_overview,
    get_monthly_trends,
    get_payment_analysis,
    get_product_performance,
    get_top_customers,
    lookup_customer,
)


def tables():
    order_ids = [f"o{i}" for i in range(30)]
    customers = ["c1" if i % 2 == 0 else "c2" for i in range(30)]
    dates = pd.date_range("2024-01-05", periods=30, freq="3D")
    return {
        "Customers": pd.DataFrame({
            "customer_id": ["c1", "c2"],
            "customer_city": ["Hyderabad", "Pune"],
            "customer_email": ["private@example.com", "other@example.com"],
        }),
        "Orders": pd.DataFrame({
            "order_id": order_ids,
            "customer_id": customers,
            "order_purchase_timestamp": dates,
            "order_status": ["completed"] * 30,
        }),
        "Payments": pd.DataFrame({
            "order_id": order_ids,
            "payment_amount": [100.0 + i for i in range(30)],
            "payment_method": ["card" if i % 2 == 0 else "upi" for i in range(30)],
        }),
        "Order items": pd.DataFrame({
            "order_id": order_ids,
            "product_id": ["p1" if i % 2 == 0 else "p2" for i in range(30)],
            "unit_price": [80.0 + i for i in range(30)],
        }),
        "Products": pd.DataFrame({
            "product_id": ["p1", "p2"],
            "product_category": ["Books", "Home"],
        }),
    }


def test_overview_reports_workspace_dataset_coverage():
    result = get_business_overview(tables())
    assert result["datasets"]["Orders"]["rows"] == 3
    assert result["kpis"]["orders"] == 3
    assert "revenue" in result["kpis"]


def test_top_customers_is_ranked_from_observed_revenue():
    result = get_top_customers(tables(), limit=2)
    assert result["available"] is True
    assert len(result["customers"]) <= 2
    assert result["ranking_basis"] == "observed_revenue"


def test_customer_lookup_excludes_contact_pii():
    result = lookup_customer(tables(), "c1")
    assert result["found"] is True
    assert result["order_count"] == 2
    assert "customer_email" not in result["profile"]


def test_monthly_trends_uses_existing_analytics_engine():
    result = get_monthly_trends(tables())
    assert result["available"] is True
    assert len(result["trends"]) >= 1


def test_product_performance_does_not_call_order_lines_units():
    result = get_product_performance(tables())
    assert result["available"] is True
    assert "order-line counts are not unit counts" in result["note"].lower()


def test_payment_analysis_groups_mapped_payment_methods():
    result = get_payment_analysis(tables())
    assert result["available"] is True
    assert len(result["payment_methods"]) == 2


def test_missing_dataset_is_reported_instead_of_invented():
    result = get_product_performance({"Products": pd.DataFrame()})
    assert result["available"] is False
    assert "Order items" in result["reason"]
