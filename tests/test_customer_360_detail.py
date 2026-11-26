import pandas as pd

from src.customer_360_detail import build_customer_360_detail


def sample_tables():
    return {
        "Customers": pd.DataFrame({
            "customer_id": ["c1", "c2"],
            "customer_city": ["Hyderabad", "Pune"],
        }),
        "Orders": pd.DataFrame({
            "order_id": ["o1", "o2", "o3"],
            "customer_id": ["c1", "c1", "c2"],
        }),
        "Order items": pd.DataFrame({
            "order_id": ["o1", "o1", "o2", "o3"],
            "product_id": ["p1", "p2", "p1", "p2"],
            "unit_price": [10, 20, 30, 40],
        }),
        "Products": pd.DataFrame({
            "product_id": ["p1", "p2"],
            "product_name": ["One", "Two"],
            "product_category": ["A", "B"],
        }),
        "Payments": pd.DataFrame({
            "order_id": ["o1", "o1", "o2", "o3"],
            "payment_amount": [5, 5, 30, 40],
        }),
        "Reviews": pd.DataFrame({
            "order_id": ["o1", "o3"],
            "rating": [5, 2],
        }),
    }


def test_customer_detail_returns_only_related_records():
    result = build_customer_360_detail(sample_tables(), "c1")
    assert len(result["customer"]) == 1
    assert result["summary"]["orders"] == 2
    assert result["summary"]["order_items"] == 3
    assert result["summary"]["payments"] == 3
    assert result["summary"]["reviews"] == 1
    assert result["summary"]["recorded_payment_total"] == 40


def test_customer_without_orders_returns_empty_transaction_tables():
    result = build_customer_360_detail(sample_tables(), "unknown")
    assert result["customer"].empty
    assert result["orders"].empty
    assert result["order_items"].empty
    assert result["payments"].empty
    assert result["reviews"].empty


def test_duplicate_product_keys_do_not_multiply_order_item_rows():
    tables = sample_tables()
    tables["Products"] = pd.concat(
        [tables["Products"], tables["Products"].iloc[[0]]],
        ignore_index=True,
    )
    result = build_customer_360_detail(tables, "c1")
    assert len(result["order_items"]) == 3
    assert result["summary"]["duplicate_product_keys_excluded"] == 1
    assert result["order_items"]["product_name"].notna().sum() == 1


def test_detail_builder_does_not_mutate_source_tables():
    tables = sample_tables()
    before = {name: frame.copy(deep=True) for name, frame in tables.items()}
    build_customer_360_detail(tables, "c1")
    for name in tables:
        pd.testing.assert_frame_equal(tables[name], before[name])
