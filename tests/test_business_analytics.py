import pandas as pd

from src.business_analytics import build_customer_360


def sample_tables():
    return {
        "Customers": pd.DataFrame({"customer_id": ["c1", "c2", "c3"]}),
        "Orders": pd.DataFrame({
            "order_id": ["o1", "o2", "o3", "o4"],
            "customer_id": ["c1", "c1", "c2", "c3"],
            "order_purchase_timestamp": pd.to_datetime([
                "2024-01-10", "2024-02-10", "2024-01-15", "2024-03-01"
            ]),
        }),
        "Payments": pd.DataFrame({
            "order_id": ["o1", "o1", "o2", "o3", "o4"],
            "payment_value": [30.0, 20.0, 50.0, 40.0, 10.0],
        }),
    }


def test_revenue_is_aggregated_per_order_before_customer_metrics():
    result = build_customer_360(sample_tables(), as_of_date="2024-03-31")
    assert result["summary"]["orders"] == 4
    assert result["summary"]["customers"] == 3
    assert result["summary"]["revenue"] == 150.0
    c1 = result["customers"].set_index("customer_id").loc["c1"]
    assert c1["observed_revenue"] == 100.0
    assert c1["frequency"] == 2


def test_repeat_rate_and_cohort_are_calculated():
    result = build_customer_360(sample_tables(), as_of_date="2024-03-31")
    assert result["summary"]["repeat_customers"] == 1
    assert abs(result["summary"]["repeat_rate"] - (1 / 3)) < 1e-9
    assert not result["cohort"].empty


def test_missing_revenue_source_does_not_invent_revenue():
    tables = sample_tables()
    tables.pop("Payments")
    result = build_customer_360(tables, as_of_date="2024-03-31")
    assert pd.isna(result["summary"]["revenue"])
    assert "revenue" in " ".join(result["limitations"]).lower()


def test_missing_order_date_disables_recency_and_cohorts():
    tables = sample_tables()
    tables["Orders"] = tables["Orders"].drop(columns=["order_purchase_timestamp"])
    result = build_customer_360(tables)
    assert result["cohort"].empty
    assert result["customers"]["recency_days"].isna().all()
