-- Disable Use cached results; use the same metrics as 08_january_raw_scan.sql.
-- month_index = 1 is January 2017 in this fixed three-month sample.
SELECT
  COUNT(*) AS transaction_rows,
  SUM(actual_amount_paid) AS total_amount_paid,
  AVG(is_auto_renew) AS auto_renew_share
FROM `kkbox-churn-analytics.kkbox.transactions_month_partitioned`
WHERE month_index = 1;
