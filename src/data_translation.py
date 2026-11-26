"""Deterministic profiling and mapping suggestions for e-commerce imports.

This module proposes mappings only. A human must confirm them before any
canonical data is saved. Original source columns are preserved in staging.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO
from pathlib import Path
import re

import numpy as np
import pandas as pd

CANONICAL = {
    "Customers": {
        "customer_id": ["customer id", "customerid", "cust id", "cust_id", "client id", "client_number", "customer number", "cust mobile", "mobile", "phone", "phone number", "telefono", "teléfono", "cliente", "customer phone"],
        "customer_name": ["customer name", "name", "full name", "nombre", "client name"],
        "customer_email": ["email", "e mail", "email address", "correo", "correo electronico"],
        "customer_phone": ["phone", "mobile", "mobile number", "cust mobile", "telephone", "telefono", "teléfono", "whatsapp"],
        "customer_city": ["city", "town", "customer city", "ciudad"],
        "customer_state": ["state", "province", "region", "customer state", "estado"],
        "customer_pincode": ["pincode", "pin code", "postal code", "zip", "zip code", "postcode"],
    },
    "Orders": {
        "order_id": ["order id", "orderid", "ord no", "order no", "order number", "order_number", "transaction id", "transaction_id", "pedido", "numero de pedido"],
        "customer_id": ["customer id", "customerid", "cust id", "client id", "cust mobile", "mobile", "phone", "email", "cliente"],
        "order_purchase_timestamp": ["order date", "order dt", "ord dt", "purchase date", "purchase_date", "created at", "created date", "fecha", "fecha de pedido", "date"],
        "order_status": ["status", "stat", "order status", "fulfilment status", "fulfillment status", "estado"],
        "order_total": ["total", "bill amt", "bill amount", "amount", "grand total", "order total", "total amount", "total_price", "importe"],
        "currency": ["currency", "currency code", "moneda"],
    },
    "Order items": {
        "order_id": ["order id", "orderid", "ord no", "order no", "pedido"],
        "product_id": ["product id", "productid", "sku", "item id", "item_id", "product code", "codigo"],
        "product_name": ["product", "product name", "sku desc", "description", "item name", "product description", "producto"],
        "quantity": ["qty", "quantity", "units", "count", "cantidad"],
        "unit_price": ["unit price", "price", "item price", "selling price", "rate", "precio"],
        "discount": ["discount", "discount amount", "disc"],
        "tax": ["tax", "gst", "vat", "tax amount"],
    },
    "Products": {
        "product_id": ["product id", "productid", "sku", "item id", "product code", "codigo"],
        "product_name": ["product", "product name", "sku desc", "description", "item name", "producto"],
        "product_category": ["category", "product category", "category name", "product type", "categoria"],
        "brand": ["brand", "manufacturer", "marca"],
    },
    "Payments": {
        "order_id": ["order id", "orderid", "ord no", "order no", "transaction id", "pedido"],
        "payment_id": ["payment id", "transaction id", "txn id", "payment reference"],
        "payment_method": ["payment method", "payment type", "method", "mode", "forma de pago"],
        "payment_amount": ["payment amount", "payment value", "amount", "paid", "paid amount", "bill amt", "importe"],
        "payment_status": ["payment status", "payment state"],
    },
    "Reviews": {
        "review_id": ["review id", "feedback id"],
        "order_id": ["order id", "orderid", "pedido"],
        "customer_id": ["customer id", "customerid", "cust id", "mobile", "phone", "email"],
        "rating": ["rating", "review score", "stars", "score", "calificacion"],
        "review_date": ["review date", "feedback date", "date"],
        "review_text": ["review", "review text", "feedback", "comment", "comments"],
    },
}

SHEET_HINTS = {
    "Customers": ["customer", "client", "buyer", "contact"],
    "Orders": ["order", "sales", "pedido", "transaction"],
    "Order items": ["item", "line", "detail", "order detail", "sku"],
    "Products": ["product", "catalog", "inventory", "sku"],
    "Payments": ["payment", "transaction", "payout"],
    "Reviews": ["review", "rating", "feedback"],
}


def normalize_name(value):
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _read_excel_sheets(payload):
    book = pd.ExcelFile(payload, engine="openpyxl")
    return {name: pd.read_excel(book, sheet_name=name, header=None) for name in book.sheet_names}


def _read_csv_sheet(payload):
    try:
        frame = pd.read_csv(payload, header=None)
    except UnicodeDecodeError:
        payload.seek(0)
        frame = pd.read_csv(payload, header=None, encoding="latin-1")
    return {"CSV": frame}


def _header_candidate(raw):
    if raw.empty:
        return 0
    best_index, best_score = 0, -1
    for index in range(min(len(raw), 15)):
        row = raw.iloc[index]
        values = [v for v in row.tolist() if pd.notna(v) and str(v).strip()]
        if not values:
            continue
        text_count = sum(not re.fullmatch(r"[-+]?\d+(\.\d+)?", str(v).strip()) for v in values)
        unique_count = len({normalize_name(v) for v in values})
        score = len(values) + text_count * 1.5 + unique_count
        if score > best_score:
            best_index, best_score = index, score
    return best_index


def _looks_like_total(row):
    values = [str(v).strip().lower() for v in row.tolist() if pd.notna(v)]
    if not values:
        return False
    first = " ".join(values[:2])
    return any(token in first for token in ["grand total", "total", "subtotal", "合計"])


def load_source_file(uploaded_file):
    """Read all sheets and identify likely header rows; return raw and profiled sheets."""
    payload = BytesIO(uploaded_file.getvalue())
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        raw_sheets = _read_csv_sheet(payload)
    elif suffix in {".xlsx", ".xlsm"}:
        raw_sheets = _read_excel_sheets(payload)
    else:
        raise ValueError("Supported formats are CSV, XLSX and XLSM.")

    sheets = {}
    for name, raw in raw_sheets.items():
        header_row = _header_candidate(raw)
        headers = []
        for i, value in enumerate(raw.iloc[header_row].tolist()):
            if pd.isna(value) or not str(value).strip():
                headers.append(f"Unnamed_{i + 1}")
            else:
                headers.append(str(value).strip())
        data = raw.iloc[header_row + 1:].copy()
        data.columns = headers
        data = data.dropna(how="all")
        total_mask = data.apply(_looks_like_total, axis=1) if not data.empty else pd.Series(dtype=bool)
        total_rows = data.loc[total_mask].copy() if len(total_mask) else pd.DataFrame()
        clean = data.loc[~total_mask].copy() if len(total_mask) else data
        sheets[name] = {
            "data": clean.reset_index(drop=True),
            "header_row": header_row + 1,
            "raw_row_count": len(data),
            "candidate_total_rows": total_rows,
            "total_rows_count": len(total_rows),
        }
    return sheets


def guess_table(sheet_name, columns):
    name = normalize_name(sheet_name)
    scores = {}
    for table, hints in SHEET_HINTS.items():
        score = sum(2 for hint in hints if hint in name)
        aliases = [normalize_name(x) for values in CANONICAL[table].values() for x in values]
        normalized_columns = [normalize_name(c) for c in columns]
        score += sum(1 for col in normalized_columns if col in aliases)
        scores[table] = score
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else None


def _profile_column(series):
    values = series.dropna().astype(str).str.strip()
    nonempty = len(values)
    unique = int(values.nunique()) if nonempty else 0
    sample = values.head(5).tolist()
    result = {
        "non_null": nonempty,
        "null_pct": round((1 - nonempty / max(len(series), 1)) * 100, 1),
        "unique": unique,
        "unique_pct": round(unique / max(nonempty, 1) * 100, 1),
        "samples": sample,
        "type_guess": "text",
        "evidence": [],
    }
    if nonempty == 0:
        result["type_guess"] = "empty"
        return result

    parsed_dates = pd.to_datetime(values, errors="coerce", dayfirst=True)
    date_rate = parsed_dates.notna().mean()
    numeric = pd.to_numeric(values.str.replace(r"[^0-9,.-]", "", regex=True).str.replace(",", "", regex=False), errors="coerce")
    numeric_rate = numeric.notna().mean()
    digits = values.str.replace(r"\D", "", regex=True)
    phone_rate = digits.str.len().between(10, 13).mean()
    email_rate = values.str.contains(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", regex=True).mean()

    if email_rate >= 0.7:
        result["type_guess"] = "email"
        result["evidence"].append("Most values resemble email addresses.")
    elif phone_rate >= 0.7:
        result["type_guess"] = "phone"
        result["evidence"].append("Most values contain 10–13 digits.")
    elif date_rate >= 0.8:
        result["type_guess"] = "date"
        result["evidence"].append(f"{date_rate:.0%} of values parse as day-first dates.")
    elif numeric_rate >= 0.85:
        result["type_guess"] = "numeric"
        result["evidence"].append(f"{numeric_rate:.0%} of values parse as numbers.")
        if numeric[ numeric.notna() ].gt(0).mean() > 0.8 and numeric.skew() > 0.5:
            result["evidence"].append("Positive, right-skewed values may represent amounts.")
    elif unique / max(nonempty, 1) > 0.95:
        result["type_guess"] = "identifier"
        result["evidence"].append("Values are almost all unique.")
    elif unique <= min(20, max(3, int(nonempty * 0.2))):
        result["type_guess"] = "category"
        result["evidence"].append("Values repeat from a relatively small set.")
    return result


def profile_frame(frame):
    return {str(column): _profile_column(frame[column]) for column in frame.columns}


def _content_score(field, profile):
    kind = profile["type_guess"]
    evidence = " ".join(profile["evidence"]).lower()
    if field in {"order_purchase_timestamp", "review_date"} and kind == "date":
        return 0.65, "Values parse consistently as dates"
    if field in {"order_total", "payment_amount", "unit_price", "discount", "tax", "quantity"} and kind == "numeric":
        if field in {"order_total", "payment_amount", "unit_price"} and "right-skewed" in evidence:
            return 0.68, "Numeric values have an amount-like distribution"
        return 0.48, "Values are numeric"
    if field in {"customer_id", "order_id", "product_id", "payment_id", "review_id"} and kind == "identifier":
        return 0.55, "Values are mostly unique"
    if field in {"customer_id"} and kind in {"phone", "email"}:
        return 0.72, "Values resemble phone numbers or email addresses"
    if field in {"order_status", "payment_status"} and kind == "category":
        return 0.62, "Values repeat from a small categorical set"
    if field in {"customer_email"} and kind == "email":
        return 0.9, "Values resemble email addresses"
    if field in {"customer_phone"} and kind == "phone":
        return 0.9, "Values resemble phone numbers"
    if field in {"rating"} and kind == "numeric":
        return 0.5, "Numeric values may be ratings; verify expected scale"
    return 0.0, ""


def suggest_mapping(frame, table_name):
    """Combine normalized header aliases and value-profile signals."""
    fields = CANONICAL[table_name]
    profiles = profile_frame(frame)
    proposals = {}
    used_columns = set()
    for field, aliases in fields.items():
        best = None
        target_names = {normalize_name(field.replace("_", " ")), *(normalize_name(x) for x in aliases)}
        for column in frame.columns:
            header = normalize_name(column)
            header_score = 0.96 if header in target_names else 0.0
            content_score, reason = _content_score(field, profiles[str(column)])
            score = max(header_score, content_score)
            if score and (best is None or score > best["confidence"]):
                best = {
                    "source_column": str(column),
                    "confidence": round(score, 2),
                    "signal": "header" if header_score >= content_score else "values",
                    "reason": "Header alias match" if header_score >= content_score else reason,
                }
        if best and best["source_column"] not in used_columns:
            proposals[field] = best
            used_columns.add(best["source_column"])
        else:
            proposals[field] = None
    return proposals, profiles


def detect_ambiguous_dates(series):
    values = series.dropna().astype(str).head(100)
    ambiguous = []
    for value in values:
        match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", value.strip())
        if match:
            first, second = int(match.group(1)), int(match.group(2))
            if first <= 12 and second <= 12 and first != second:
                ambiguous.append(value)
    return ambiguous


def normalize_amount(value):
    """Parse common INR, BRL and plain numeric amount representations."""
    if pd.isna(value):
        return np.nan
    raw = str(value).strip().replace("₹", "").replace("R$", "").replace("$", "").replace("€", "")
    raw = raw.replace("INR", "").replace("BRL", "").replace(" ", "")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        tail = raw.rsplit(",", 1)[-1]
        raw = raw.replace(",", ".") if len(tail) in (1, 2) else raw.replace(",", "")
    return pd.to_numeric(raw, errors="coerce")


def normalize_phone(value, country_code="91"):
    """Normalize phone digits; preserve the local number as text."""
    if pd.isna(value):
        return pd.NA
    digits = re.sub(r"\D", "", str(value))
    if digits.startswith(country_code) and len(digits) > 10:
        digits = digits[len(country_code):]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits or pd.NA


def normalize_status(value, mapping):
    if pd.isna(value):
        return pd.NA
    return mapping.get(str(value).strip().lower(), "unmapped")


def canonicalize_frame(frame, mapping, table_name, date_format=None, status_mapping=None, currency=""):
    """Translate confirmed source->canonical mapping and preserve all source columns."""
    # Preserve every original source field in a namespaced staging column before
    # applying canonical names. This prevents unmapped business attributes from
    # disappearing during translation.
    output = frame.copy()
    for source_column in list(frame.columns):
        preserved_name = f"source__{source_column}"
        if preserved_name not in output.columns:
            output[preserved_name] = frame[source_column]
    rename = {}
    for canonical, source in mapping.items():
        if source and source in output.columns:
            rename[source] = canonical
    output = output.rename(columns=rename)
    if "order_purchase_timestamp" in output:
        if date_format == "dayfirst":
            output["order_purchase_timestamp"] = pd.to_datetime(output["order_purchase_timestamp"], errors="coerce", dayfirst=True)
        elif date_format == "monthfirst":
            output["order_purchase_timestamp"] = pd.to_datetime(output["order_purchase_timestamp"], errors="coerce", dayfirst=False)
        else:
            output["order_purchase_timestamp"] = pd.to_datetime(output["order_purchase_timestamp"], errors="coerce", dayfirst=True)
    for field in ["order_total", "payment_amount", "unit_price", "discount", "tax", "quantity"]:
        if field in output:
            output[field] = output[field].map(normalize_amount)
    for field in ["customer_id", "customer_phone"]:
        if field in output and (field == "customer_phone" or output[field].astype(str).str.fullmatch(r"\+?[0-9()\- ]{10,}").mean() > 0.7):
            output[field] = output[field].map(normalize_phone).astype("string")
    if "order_status" in output:
        output["order_status_raw"] = output["order_status"].astype("string")
        if status_mapping:
            output["order_status"] = output["order_status"].map(lambda x: normalize_status(x, status_mapping))
    if currency and "currency" not in output:
        output["currency"] = currency
    return output
