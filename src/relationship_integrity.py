"""Cross-dataset key integrity checks for canonical e-commerce tables."""
from __future__ import annotations

import pandas as pd


RELATIONSHIPS = [
    ("Orders", "customer_id", "Customers", "customer_id", "Orders → Customers"),
    ("Order items", "order_id", "Orders", "order_id", "Order items → Orders"),
    ("Payments", "order_id", "Orders", "order_id", "Payments → Orders"),
    ("Reviews", "order_id", "Orders", "order_id", "Reviews → Orders"),
    ("Order items", "product_id", "Products", "product_id", "Order items → Products"),
]


def _clean_key(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip()
    return values.mask(values.eq(""))


def _empty_report():
    return {
        "relationship": "",
        "source_table": "",
        "source_field": "",
        "target_table": "",
        "target_field": "",
        "source_rows": 0,
        "missing_key_rows": 0,
        "matched_rows": 0,
        "unmatched_rows": 0,
        "match_rate": None,
        "duplicate_target_key_values": 0,
        "status": "Unavailable",
        "details": "Required tables or key fields are not uploaded.",
    }


def audit_relationships(tables: dict) -> dict:
    """Audit canonical foreign-key coverage without changing any source table.

    Duplicate target keys are counted distinctly from unmatched source keys.
    A match means the source key exists in the target key set; the audit does
    not deduplicate or repair either dataset.
    """
    reports = []
    issues = {}

    for source_table, source_field, target_table, target_field, label in RELATIONSHIPS:
        source = tables.get(source_table, pd.DataFrame())
        target = tables.get(target_table, pd.DataFrame())
        report = _empty_report()
        report.update({
            "relationship": label,
            "source_table": source_table,
            "source_field": source_field,
            "target_table": target_table,
            "target_field": target_field,
        })

        if source.empty or target.empty or source_field not in source.columns or target_field not in target.columns:
            reports.append(report)
            issues[label] = pd.DataFrame()
            continue

        source_keys = _clean_key(source[source_field])
        target_keys = _clean_key(target[target_field])
        valid_target = target_keys.dropna()
        duplicate_mask = valid_target.duplicated(keep=False)
        target_key_set = set(valid_target.unique().tolist())

        missing_mask = source_keys.isna()
        unmatched_mask = source_keys.notna() & ~source_keys.isin(target_key_set)
        matched_mask = source_keys.notna() & source_keys.isin(target_key_set)
        report.update({
            "source_rows": int(len(source)),
            "missing_key_rows": int(missing_mask.sum()),
            "matched_rows": int(matched_mask.sum()),
            "unmatched_rows": int(unmatched_mask.sum()),
            "match_rate": float(matched_mask.sum() / max(int((~missing_mask).sum()), 1)) if (~missing_mask).any() else None,
            "duplicate_target_key_values": int(valid_target[duplicate_mask].nunique()),
        })
        if report["missing_key_rows"] or report["unmatched_rows"] or report["duplicate_target_key_values"]:
            report["status"] = "Review"
        else:
            report["status"] = "Healthy"
        report["details"] = (
            f"{report['matched_rows']:,} source rows matched; "
            f"{report['unmatched_rows']:,} unmatched; "
            f"{report['missing_key_rows']:,} missing source keys; "
            f"{report['duplicate_target_key_values']:,} duplicate target key values."
        )

        issue_frame = source.loc[missing_mask | unmatched_mask].copy()
        issue_frame["relationship_issue"] = "Missing key"
        issue_frame.loc[unmatched_mask, "relationship_issue"] = "Unmatched key"
        issues[label] = issue_frame
        reports.append(report)

    report_frame = pd.DataFrame(reports)
    available = report_frame[report_frame["status"] != "Unavailable"]
    summary = {
        "relationships_checked": int(len(available)),
        "healthy_relationships": int((available["status"] == "Healthy").sum()),
        "relationships_needing_review": int((available["status"] == "Review").sum()),
        "unavailable_relationships": int((report_frame["status"] == "Unavailable").sum()),
        "unmatched_source_rows": int(report_frame["unmatched_rows"].sum()),
        "missing_source_key_rows": int(report_frame["missing_key_rows"].sum()),
    }
    return {"summary": summary, "relationships": report_frame, "issues": issues}
