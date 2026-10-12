"""Prepare a deterministic user sample for the BigQuery tutorial.

Run from any directory: python scripts/prepare_bigquery_sample.py
Uses only the Python standard library. User-level exports stay under data/.
"""

import csv
import hashlib
import heapq
import json
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "bigquery_upload"
REPORT = ROOT / "reports" / "bigquery_sample_manifest.json"
SAMPLE_USERS = 10_000
CUTOFF = date(2017, 2, 28)
START = CUTOFF - timedelta(days=89)
SALT = "kkbox-bigquery-v1:"


def main():
    # Hash ranking samples users independently of their outcomes and file order.
    with (RAW / "train_v2.csv").open(newline="") as f:
        labels = list(csv.DictReader(f))
    assert len({row["msno"] for row in labels}) == len(labels)
    assert all(row["is_churn"] in {"0", "1"} for row in labels)
    assert len(labels) >= SAMPLE_USERS
    selected = heapq.nsmallest(
        SAMPLE_USERS,
        labels,
        key=lambda row: (
            hashlib.sha256((SALT + row["msno"]).encode()).hexdigest(),
            row["msno"],
        ),
    )
    users = {row["msno"] for row in selected}
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "cohort_sample.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["msno", "is_churn"])
        writer.writeheader()
        writer.writerows(selected)

    scanned = exported = 0
    users_with_transactions = set()
    transaction_path = OUT / "transactions_sample.csv"
    temporary = transaction_path.with_suffix(".csv.partial")
    with (RAW / "transactions.csv").open(newline="") as source:
        header = next(csv.reader([source.readline()]))
        assert header[0] == "msno"
        day_index = header.index("transaction_date")
        lower = START.strftime("%Y%m%d")
        upper = CUTOFF.strftime("%Y%m%d")
        with temporary.open("w", newline="") as target:
            writer = csv.writer(target)
            writer.writerow(header)
            for line in source:
                scanned += 1
                # Avoid parsing all 21M rows: the source's first field is msno.
                if line.split(",", 1)[0] not in users:
                    continue
                row = next(csv.reader([line]))
                assert len(row) == len(header)
                if lower <= row[day_index] <= upper:
                    transaction_day = date(
                        int(row[day_index][:4]),
                        int(row[day_index][4:6]),
                        int(row[day_index][6:8]),
                    )
                    assert START <= transaction_day <= CUTOFF
                    writer.writerow(row)
                    exported += 1
                    users_with_transactions.add(row[0])
    assert exported > 0
    assert users_with_transactions <= users
    temporary.replace(transaction_path)

    files = {}
    for name in ["cohort_sample.csv", "transactions_sample.csv"]:
        path = OUT / name
        assert path.stat().st_size < 100_000_000
        files[name] = {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    summary = {
        "purpose": "BigQuery SQL migration exercise; not new model validation",
        "cohort_source": "train_v2.csv",
        "transaction_source": "transactions.csv",
        "sampling": "10,000 lowest SHA256(salt + msno), tie-break by msno",
        "sampling_salt": SALT,
        "full_cohort_users": len(labels),
        "sample_users": len(selected),
        "sample_churn_users": sum(int(row["is_churn"]) for row in selected),
        "window_start_inclusive": START.isoformat(),
        "feature_cutoff_inclusive": CUTOFF.isoformat(),
        "source_transaction_rows_scanned": scanned,
        "sample_transaction_rows": exported,
        "sample_users_with_transactions": len(users_with_transactions),
        "sample_users_without_transactions": len(users - users_with_transactions),
        "duplicates": "Preserved to match existing transaction feature SQL",
        "cloud_execution_completed": False,
        "files": files,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
