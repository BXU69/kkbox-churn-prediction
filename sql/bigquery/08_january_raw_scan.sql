-- Disable Use cached results in query settings before benchmarking.
SELECT
  COUNT(*) AS transaction_rows,
  SUM(actual_amount_paid) AS total_amount_paid,
  AVG(is_auto_renew) AS auto_renew_share
FROM `kkbox-churn-analytics.kkbox.transactions_sample`
WHERE transaction_date BETWEEN 20170101 AND 20170131;
