# BigQuery and Tableau reproduction guide

## Scope and recorded results

This extension demonstrates cloud SQL, a Python client query, and an interactive
dashboard on a deterministic 10,000-user sample. It is separate from the larger
local model evaluation. It does not migrate listening features or model training
to BigQuery, and the dashboard is not a live BigQuery connection.

The sample contains 27,094 transactions from 9,707 users during the inclusive
90-day window 2016-12-01 to 2017-02-28. All 10,000 users remain in the feature
table, including 293 without transactions. There are 910 observed churners.

Sampling, feature parity, and aggregate-export checks were executed locally.
Cloud execution was verified from user-provided query screenshots and Python
output. The published dashboard was checked in a signed-out browser on
October 12, 2026; its unfiltered charts and explanatory text rendered correctly.
The user also demonstrated linked filtering in the editor: selecting the
31–90 day group leaves 193 users and auto-renew group rates of 63.00%,
46.15%, and 61.25%. Public interaction was not separately automated.

## 1. Prepare the sample locally

Use the existing local project environment and the official competition data.
From the repository root:

```bash
python scripts/prepare_bigquery_sample.py
```

The script selects the 10,000 lowest SHA256 hashes of a fixed salt plus user ID
from `train_v2.csv`. Selection does not depend on churn labels or file order.
It scans `transactions.csv` and retains every transaction for those users in
the fixed window, preserving duplicates to match the original feature SQL.

Outputs:

- `data/bigquery_upload/cohort_sample.csv`
- `data/bigquery_upload/transactions_sample.csv`
- `reports/bigquery_sample_manifest.json`

User-level files stay under the ignored `data/` directory. Sample preparation
does not prove cloud execution; rerunning it resets that manifest's cloud status.

## 2. Create and load BigQuery tables

The recorded project ID is `kkbox-churn-analytics`; use your own ID and replace
it in SQL files and the Python script when reproducing. Create dataset `kkbox`
in the US multi-region. BigQuery sandbox can be used without a billing account.

In the console, create native tables from the CSV uploads, skip one header row,
and use these schemas in CSV column order:

| Table | Schema |
|---|---|
| `cohort_sample` | `msno STRING`, `is_churn INTEGER` |
| `transactions_sample` | `msno STRING`, `payment_method_id INTEGER`, `payment_plan_days INTEGER`, `plan_list_price INTEGER`, `actual_amount_paid INTEGER`, `is_auto_renew INTEGER`, `transaction_date INTEGER`, `membership_expire_date INTEGER`, `is_cancel INTEGER` |

Use NULLABLE mode. The raw dates remain YYYYMMDD integers at this loading stage.
Check field spelling, particularly `plan_list_price`.

Run these files in sequence:

1. `sql/bigquery/01_cohort_audit.sql`
2. `sql/bigquery/02_transaction_audit.sql`
3. `sql/bigquery/05_create_month_range_transactions.sql`
4. `sql/bigquery/06_create_transaction_features.sql`
5. `sql/bigquery/07_export_transaction_features.sql`

The CREATE TABLE statements should be run once for each new output table.
Download the complete feature result as
`data/bigquery_upload/bigquery_user_transaction_features.csv`.

### Historical partition expiration

`03_create_partitioned_transactions.sql` and `04_partitioned_row_check.sql`
preserve an unsuccessful date-partitioning experiment; skip them in the working
pipeline. The sandbox assigned a 60-day partition lifetime, measured from each
historical partition date, leaving zero rows in the date-partitioned table.
The raw source retained all 27,094 rows.

The working table `transactions_month_partitioned` uses an integer range:
month index 0 = December 2016, 1 = January 2017, 2 = February 2017. It clusters
by `msno` and requires a month-index filter. Integer-range partitioning does
not support time-based partition expiration; normal sandbox table expiration
still applies. Real transaction dates are preserved.

[BigQuery sandbox](https://docs.cloud.google.com/bigquery/docs/sandbox) ·
[Partition expiration](https://docs.cloud.google.com/bigquery/docs/managing-partitioned-tables#partition-expiration)

## 3. Verify SQL parity

```bash
python scripts/verify_bigquery_features.py
```

This reruns `sql/transaction_features_90d.sql` in DuckDB on the same sampled
transactions, left joins the sample cohort, and compares by user ID. It checks
the cohort, schema, label, seven features, and null positions. Count/label values
must match exactly; averages use absolute and relative tolerance of 1e-10.

All comparisons passed. The largest observed difference was approximately
1.11e-16 for auto-renew share. See `reports/bigquery_feature_parity.csv` and
`reports/bigquery_feature_parity_summary.json`. This is sample SQL parity,
not validation of the full source data or the predictive model.

## 4. Compare scans with result caching disabled

Disable **Use cached results** in query settings, then run files 08 and 09
separately. Both compute January transaction count, amount paid, and auto-renew
share. Recorded results match at the displayed precision: 9,315 transactions,
amount-paid sum 1,207,366, auto-renew share approximately 92.52%.

| Query | Processed data | Duration | Billed data | Slot-ms |
|---|---:|---:|---:|---:|
| Raw table | 635.02 KB | 190 ms | 10 MB | 9 |
| Month partition | 218.32 KB | 202 ms | 10 MB | 10 |

The scan reduction is approximately 65.6%, computed from displayed units.
No latency or billed-byte reduction was observed. These single runs on a small
sample are not a performance benchmark for the full dataset. There is no
`msno` filter, so clustering benefits were not isolated. Billed bytes do not
establish an actual monetary charge. Exact full-precision average values were
not available from the screenshots.

See `reports/bigquery_scan_comparison.csv` and the two January job JSON reports.

## 5. Query with Python

In authenticated Google Cloud Shell:

```bash
python3 -m pip install --user google-cloud-bigquery
python3 query_bigquery_summary.py
```

Create the file in the Cloud Shell editor using the contents of
`scripts/query_bigquery_summary.py`. The client uses the current authenticated
account; no service-account key is needed for this Cloud Shell workflow. A local
environment needs its own Application Default Credentials setup.

The script disables result caching and sets `maximum_bytes_billed` to 50 MiB.
That limit is data volume, not currency. Recorded execution returned the expected
summary, processed 160,000 bytes, and reported 10,485,760 billed bytes with
`cache_hit = false`. See `reports/bigquery_python_summary.json`.

[Official Python quickstart](https://docs.cloud.google.com/bigquery/docs/quickstarts/quickstart-client-libraries)

## 6. Prepare Tableau data

Run `sql/bigquery/10_tableau_transaction_segments.sql` and download all results
as `reports/tableau/kkbox_transaction_segments.csv`. The ten groups are mutually
exclusive combinations of transaction recency and auto-renew history, with
counts, observed churners, transaction counts, and group churn rates.

The exported counts matched the local reference exactly; six-decimal churn rates
matched within 1e-6. Totals are 10,000 users, 910 churners, and 27,094 transactions.
See `reports/tableau/segment_export_validation.json`. The local reference CSV is
retained alongside the cloud export for inspection.

## 7. Recreate the dashboard in Tableau Public web authoring

Upload only the aggregate segment CSV. Create the calculated field
`Weighted Churn Rate`:

```text
SUM([Churned Users]) / SUM([Users])
```

Do not average the precomputed group churn rates after regrouping.

| Worksheet | Rows | Columns | Labels |
|---|---|---|---|
| Churn by Recency | Recency Segment | Weighted Churn Rate | Weighted Churn Rate |
| Users by Recency | Recency Segment | SUM(Users) | SUM(Users) |
| Churn by Auto-Renew | Auto Renew Segment | Weighted Churn Rate | Weighted Churn Rate |

Use horizontal bars. Format rates as percentages with two decimals and counts
as integers. Add user counts and churner counts to rate-chart tooltips.

Arrange the three worksheets vertically in a fixed-size dashboard. Use the first
worksheet as a filter for the other two. Show the 10,000-user sample and Dec
2016–Feb 2017 transaction window in the title. Explain the click/reset interaction,
the February 28, 2017 recency cutoff, and that the rates are observational.

### Interpretation

Longer gaps since the last recorded transaction are associated with higher
observed churn in this sample. The 31–90 day group has 193 users and 61.14%
churn; the no-transaction group has 293 users and 85.67% churn. Group sizes
should accompany rates. Auto-renew groups summarize all transactions in the
window, not a user's current subscription setting. These comparisons do not
measure intervention effects or establish deployment readiness.

## Published dashboard

[KKBox Churn Overview — BigQuery & Tableau](https://public.tableau.com/app/profile/becca.xu/viz/KKBoxChurnOverviewBigQueryTableau/KKBoxChurnOverview)

The published workbook uses an uploaded CSV extract. Changes in BigQuery are
not automatically reflected; rerun the aggregate query and update the workbook
data to refresh it. All exported user-level data remains local and excluded
from Git; public artifacts contain aggregate results only.
