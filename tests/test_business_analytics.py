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
    assert result["cohort"].empty
    assert any("fewer than 30 orders" in note for note in result["limitations"])


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



def test_cohort_is_enabled_at_thirty_orders():
    tables = {
        "Orders": pd.DataFrame({
            "order_id": [f"o{i}" for i in range(30)],
            "customer_id": [f"c{i % 10}" for i in range(30)],
            "order_purchase_timestamp": pd.date_range("2024-01-01", periods=30, freq="7D"),
        }),
        "Payments": pd.DataFrame({
            "order_id": [f"o{i}" for i in range(30)],
            "payment_value": [25.0 + i for i in range(30)],
        }),
    }
    result = build_customer_360(tables, as_of_date="2025-01-01")
    assert not result["cohort"].empty



def test_customer_only_upload_produces_profile_and_signup_trend():
    tables = {"Customers": pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c3"],
        "customer_name": ["A", "B", "C", "C duplicate"],
        "customer_email": ["a@example.com", "b@example.com", None, "c@example.com"],
        "customer_city": ["Hyderabad", "Pune", "Hyderabad", "Hyderabad"],
        "customer_country": ["India", "India", "India", "India"],
        "signup_date": pd.to_datetime(["2026-01-05", "2026-01-20", "2026-02-03", "2026-02-03"]),
    })}
    result = build_customer_360(tables)
    assert result["summary"]["customer_only"] is True
    assert result["summary"]["customers"] == 3
    assert result["summary"]["duplicate_customer_rows"] == 2
    assert not result["customer_profile"]["signup_monthly"].empty
    assert "revenue" not in result["summary"]
    assert any("Orders have not been uploaded" in note for note in result["limitations"])


def test_customer_only_without_signup_date_still_shows_customer_counts():
    result = build_customer_360({"Customers": pd.DataFrame({"customer_id": ["c1", "c2"]})})
    assert result["summary"]["customers"] == 2
    assert result["customer_profile"]["signup_monthly"].empty
    assert any("signup" in note.lower() for note in result["limitations"])



def test_customer_only_quality_flags_preserve_duplicate_and_invalid_rows():
    tables = {"Customers": pd.DataFrame({
        "customer_id": ["c1", "c1", None, "c4"],
        "customer_email": ["same@example.com", "same@example.com", "bad-email", None],
        "customer_name": ["A", "A duplicate", "Missing ID", "D"],
        "customer_city": ["Hyderabad", "Hyderabad", "Pune", None],
        "signup_date": ["2026-01-01", "2026-01-01", "not-a-date", "2026-02-01"],
    })}
    result = build_customer_360(tables)
    quality = result["summary"]["data_quality"]
    assert len(result["customers"]) == 4
    assert quality["unique_customers"] == 2
    assert quality["missing_customer_id_rows"] == 1
    assert quality["duplicate_customer_id_values"] == 1
    assert quality["duplicate_customer_id_rows"] == 2
    assert quality["duplicate_email_values"] == 1
    assert quality["invalid_email_rows"] == 1
    assert quality["invalid_signup_date_rows"] == 1
    assert result["customers"]["data_quality_duplicate_id"].sum() == 2


def test_customer_only_segments_use_unique_ids_and_profile_completeness():
    tables = {"Customers": pd.DataFrame({
        "customer_id": ["c1", "c2", "c2", "c3"],
        "customer_name": ["A", "B", "B duplicate", None],
        "customer_email": ["a@example.com", "b@example.com", "b@example.com", None],
        "customer_city": ["Hyderabad", "Pune", "Pune", "Delhi"],
        "signup_date": ["2026-01-05", "2026-01-20", "2026-01-20", None],
    })}
    result = build_customer_360(tables)
    segments = result["customer_segments"]
    assignments = segments["assignments"]
    assert assignments["customer_id"].nunique() == 3
    assert assignments["profile_completeness"].value_counts().to_dict() == {
        "Complete profile": 2,
        "Needs enrichment": 1,
    }
    assert segments["signup_cohort"]["customers"].sum() == 3
    assert "Signup date unavailable" in assignments["signup_cohort"].values


def test_customer_segments_work_without_optional_attributes():
    result = build_customer_360({"Customers": pd.DataFrame({"customer_id": ["c1", "c2"]})})
    assignments = result["customer_segments"]["assignments"]
    assert len(assignments) == 2
    assert assignments["profile_completeness"].eq("Not assessed - no profile attributes mapped").all()
