"""Run in authenticated Cloud Shell with google-cloud-bigquery installed."""

import json
from pathlib import Path

from google.cloud import bigquery


def main():
    client = bigquery.Client(project="kkbox-churn-analytics", location="US")
    sql = """
    SELECT
      COUNT(*) AS total_users,
      SUM(is_churn) AS churned_users,
      ROUND(AVG(is_churn) * 100, 2) AS churn_rate_pct,
      COUNTIF(has_transaction_90d = 0) AS users_without_transactions
    FROM `kkbox-churn-analytics.kkbox.user_transaction_features`
    """
    config = bigquery.QueryJobConfig(
        use_query_cache=False,
        maximum_bytes_billed=50 * 1024 * 1024,
    )
    job = client.query(sql, job_config=config)
    rows = list(job.result())
    assert len(rows) == 1, "Expected one aggregate summary row"
    summary = dict(rows[0])
    report = {
        "summary": summary,
        "job": {
            "bytes_processed": job.total_bytes_processed,
            "bytes_billed": job.total_bytes_billed,
            "cache_hit": job.cache_hit,
        },
    }
    print(json.dumps(report, indent=2))
    output = Path("bigquery_python_summary.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved aggregate report: {output}")


if __name__ == "__main__":
    main()
