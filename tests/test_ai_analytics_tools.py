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
    return {
        "Customers": pd.DataFrame({
            "customer_id": ["c1", "c2"],
            "customer_city": ["Hyderabad", "Pune"],
            "customer_email": ["private@example.com", "other@example.com"],
        }),
        "Orders": pd.DataFrame({
            "order_id": ["o1", "o2", "o3"],
            "customer_id": ["c1", "c1", "c2"],
            "order_purchase_timestamp": pd.to_datetime(["2024-01-05", "2024-02-05", "2024-02-10"]),
            "order_status": ["completed", "completed", "cancelled"],
        }),
        "Payments": pd.DataFrame({
            "order_id": ["o1", "o2", "o3"],
            "payment_amount": [100.0, 50.0, 25.0],
            "payment_method": ["card", "upi", "card"],
        }),
        "Order items": pd.DataFrame({
            "order_id": ["o1", "o2", "o3"],
            "product_id": ["p1", "p2", "p1"],
            "unit_price": [80.0, 40.0, 20.0],
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
