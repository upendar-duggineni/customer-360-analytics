import pandas as pd

from src.data_translation import (
    load_source_file, profile_frame, suggest_mapping, normalize_amount,
    normalize_phone, canonicalize_frame,
)


class Upload:
    def __init__(self, name, data):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


def test_indian_d2c_headers_and_content_mapping():
    frame = pd.DataFrame({
        "Ord No": ["A-1", "A-2", "A-3"],
        "Cust Mobile": ["+91 98765 43210", "09876543211", "9876543212"],
        "Bill Amt (INR)": ["₹1,299.00", "₹2,450.00", "₹899.00"],
        "Ord Dt": ["15/04/2026", "16/04/2026", "17/04/2026"],
        "Stat": ["Delivered", "RTO", "Cancelled"],
        "SKU Desc": ["Shirt", "Shoes", "Bag"],
        "Qty": [1, 2, 1],
        "Pincode": ["500001", "500002", "500003"],
        "Col_9": ["x", "y", "z"],
    })
    proposals, profiles = suggest_mapping(frame, "Orders")
    assert proposals["order_id"]["source_column"] == "Ord No"
    assert proposals["order_purchase_timestamp"]["source_column"] == "Ord Dt"
    assert proposals["order_status"]["source_column"] == "Stat"
    assert profiles["Cust Mobile"]["type_guess"] == "phone"


def test_amount_and_indian_phone_normalization():
    assert normalize_amount("₹1,299.00") == 1299.0
    assert normalize_amount("R$ 1.299,00") == 1299.0
    assert normalize_amount("1299") == 1299.0
    assert normalize_phone("+91 98765 43210") == "9876543210"


def test_excel_multiple_sheets_and_header_row_detection():
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([["Monthly Export"], ["Generated today"], ["Ord No", "Ord Dt"], ["A1", "2026-01-01"]]).to_excel(writer, sheet_name="Orders", header=False, index=False)
        pd.DataFrame([["Customer Export"], ["CustomerID"], ["C1"]]).to_excel(writer, sheet_name="Customers", header=False, index=False)
    sheets = load_source_file(Upload("company.xlsx", buffer.getvalue()))
    assert set(sheets) == {"Orders", "Customers"}
    assert sheets["Orders"]["header_row"] == 3
    assert sheets["Orders"]["data"].iloc[0]["Ord No"] == "A1"


def test_canonicalization_preserves_original_columns():
    frame = pd.DataFrame({"Ord No": ["A1"], "Bill Amt": ["₹1,299.00"], "Extra": ["keep me"]})
    translated = canonicalize_frame(
        frame, {"order_id": "Ord No", "order_total": "Bill Amt"}, "Orders",
        currency="INR"
    )
    assert translated.loc[0, "order_id"] == "A1"
    assert translated.loc[0, "order_total"] == 1299.0
    assert translated.loc[0, "source__Extra"] == "keep me"
