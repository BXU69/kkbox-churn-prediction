"""Compare a downloaded BigQuery feature CSV with the existing DuckDB SQL.

Run with the project's environment: python scripts/verify_bigquery_features.py
Only aggregate comparison reports are written outside the ignored data folder.
"""

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "bigquery_upload"
REPORTS = ROOT / "reports"
FLOAT_COLUMNS = {"auto_renew_share_90d", "avg_plan_days_90d"}


def main():
    cohort = pd.read_csv(DATA / "cohort_sample.csv", dtype={"msno": str})
    cloud = pd.read_csv(
        DATA / "bigquery_user_transaction_features.csv", dtype={"msno": str}
    )
    for frame in [cohort, cloud]:
        if frame["msno"].isna().any() or frame["msno"].duplicated().any():
            raise ValueError("Missing or duplicate user identifiers")
    if set(cohort["msno"]) != set(cloud["msno"]):
        raise ValueError("Cloud export does not contain exactly the sample users")

    with duckdb.connect() as con:
        con.register("cohort_users", cohort[["msno"]])
        features = con.execute(
            (ROOT / "sql" / "transaction_features_90d.sql").read_text(),
            [str(DATA / "transactions_sample.csv"),
             "2016-12-01", "2017-02-28", "2017-02-28"],
        ).df()
    local = cohort.merge(features, on="msno", how="left", validate="one_to_one")
    local["has_transaction_90d"] = local["transaction_rows_90d"].notna().astype(int)
    for column in ["transaction_rows_90d", "transaction_days_90d", "cancel_rows_90d"]:
        local[column] = local[column].fillna(0).astype("int64")
    if set(local.columns) != set(cloud.columns):
        raise ValueError("Cloud and local feature columns differ")
    local = local.set_index("msno").sort_index()
    cloud = cloud.set_index("msno").reindex(local.index)

    comparisons = []
    for column in local.columns:
        expected = pd.to_numeric(local[column], errors="raise").to_numpy(dtype=float)
        actual = pd.to_numeric(cloud[column], errors="raise").to_numpy(dtype=float)
        expected_missing = np.isnan(expected)
        actual_missing = np.isnan(actual)
        present = ~expected_missing & ~actual_missing
        null_mismatches = expected_missing != actual_missing
        if not np.isfinite(expected[present]).all() or not np.isfinite(actual[present]).all():
            raise ValueError(f"Non-finite values in {column}")
        tolerance = 1e-10 if column in FLOAT_COLUMNS else 0.0
        differences = np.abs(expected[present] - actual[present])
        value_mismatches = ~np.isclose(
            expected[present], actual[present], rtol=tolerance, atol=tolerance
        )
        mismatch_count = int(null_mismatches.sum() + value_mismatches.sum())
        comparisons.append({
            "column": column,
            "compared_users": len(local),
            "local_nulls": int(expected_missing.sum()),
            "bigquery_nulls": int(actual_missing.sum()),
            "null_mismatches": int(null_mismatches.sum()),
            "value_mismatches": int(value_mismatches.sum()),
            "max_absolute_difference": float(differences.max()) if len(differences) else 0.0,
            "absolute_tolerance": tolerance,
            "relative_tolerance": tolerance,
            "passed": mismatch_count == 0,
        })
    report = pd.DataFrame(comparisons)
    REPORTS.mkdir(parents=True, exist_ok=True)
    report.to_csv(REPORTS / "bigquery_feature_parity.csv", index=False)
    summary = {
        "reference": "existing sql/transaction_features_90d.sql on sampled transactions",
        "bigquery_export": "data/bigquery_upload/bigquery_user_transaction_features.csv",
        "users": len(local),
        "compared_columns": len(report),
        "feature_columns": len(report) - 1,
        "label_compared": True,
        "all_passed": bool(report["passed"].all()),
        "total_null_mismatches": int(report["null_mismatches"].sum()),
        "total_value_mismatches": int(report["value_mismatches"].sum()),
        "scope": "Parity for this sample only; not full-data or model validation",
        "duckdb_version": duckdb.__version__,
        "pandas_version": pd.__version__,
    }
    (REPORTS / "bigquery_feature_parity_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(report.to_string(index=False))
    print(json.dumps(summary, indent=2))
    if not summary["all_passed"]:
        raise SystemExit("BigQuery feature parity failed; see aggregate reports")


if __name__ == "__main__":
    main()
