import pandas as pd

from src.relationship_integrity import audit_relationships


def test_relationship_audit_detects_missing_unmatched_and_duplicate_keys():
    tables = {
        "Customers": pd.DataFrame({"customer_id": ["c1", "c1", "c2"]}),
        "Orders": pd.DataFrame({
            "order_id": ["o1", "o2", "o3"],
            "customer_id": ["c1", "missing", None],
        }),
        "Order items": pd.DataFrame({
            "order_id": ["o1", "bad-order"],
            "product_id": ["p1", "missing-product"],
        }),
        "Products": pd.DataFrame({"product_id": ["p1", "p1"]}),
    }
    result = audit_relationships(tables)
    customer_orders = result["relationships"].set_index("relationship").loc["Orders → Customers"]
    assert customer_orders["matched_rows"] == 1
    assert customer_orders["unmatched_rows"] == 1
    assert customer_orders["missing_key_rows"] == 1
    assert customer_orders["duplicate_target_key_values"] == 1
    assert customer_orders["status"] == "Review"
    assert len(result["issues"]["Orders → Customers"]) == 2


def test_relationship_audit_marks_missing_tables_unavailable():
    result = audit_relationships({"Customers": pd.DataFrame({"customer_id": ["c1"]})})
    assert result["summary"]["unavailable_relationships"] == 5
    assert result["summary"]["relationships_checked"] == 0


def test_relationship_audit_does_not_mutate_input_tables():
    orders = pd.DataFrame({"order_id": ["o1"], "customer_id": ["c1"]})
    original = orders.copy(deep=True)
    audit_relationships({"Orders": orders, "Customers": pd.DataFrame({"customer_id": ["c1"]})})
    pd.testing.assert_frame_equal(orders, original)


def test_relationship_audit_handles_whitespace_and_empty_keys():
    result = audit_relationships({
        "Customers": pd.DataFrame({"customer_id": ["c1"]}),
        "Orders": pd.DataFrame({"order_id": ["o1"], "customer_id": [" c1 "]}),
    })
    row = result["relationships"].set_index("relationship").loc["Orders → Customers"]
    assert row["matched_rows"] == 1
    assert row["status"] == "Healthy"
