-- Download the complete result as CSV to local data/bigquery_upload/.
-- This user-level export must not be committed or published to Tableau Public.
SELECT
  msno,
  is_churn,
  transaction_rows_90d,
  transaction_days_90d,
  cancel_rows_90d,
  auto_renew_share_90d,
  avg_plan_days_90d,
  days_since_last_transaction_90d,
  has_transaction_90d
FROM `kkbox-churn-analytics.kkbox.user_transaction_features`
ORDER BY msno;
