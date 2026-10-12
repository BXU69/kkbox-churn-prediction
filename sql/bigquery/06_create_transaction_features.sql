-- Match sql/transaction_features_90d.sql and the notebook's cohort left join.
-- Preserve users with no transactions; missing rates/recency remain NULL.
CREATE TABLE `kkbox-churn-analytics.kkbox.user_transaction_features`
AS
WITH features AS (
  SELECT
    msno,
    COUNT(*) AS transaction_rows_90d,
    COUNT(DISTINCT transaction_day) AS transaction_days_90d,
    COUNTIF(is_cancel = 1) AS cancel_rows_90d,
    AVG(is_auto_renew) AS auto_renew_share_90d,
    AVG(payment_plan_days) AS avg_plan_days_90d,
    DATE_DIFF(DATE '2017-02-28', MAX(transaction_day), DAY)
      AS days_since_last_transaction_90d
  FROM `kkbox-churn-analytics.kkbox.transactions_month_partitioned`
  WHERE month_index BETWEEN 0 AND 2
    AND transaction_day BETWEEN DATE '2016-12-01' AND DATE '2017-02-28'
  GROUP BY msno
)
SELECT
  c.msno,
  c.is_churn,
  COALESCE(f.transaction_rows_90d, 0) AS transaction_rows_90d,
  COALESCE(f.transaction_days_90d, 0) AS transaction_days_90d,
  COALESCE(f.cancel_rows_90d, 0) AS cancel_rows_90d,
  f.auto_renew_share_90d,
  f.avg_plan_days_90d,
  f.days_since_last_transaction_90d,
  IF(f.msno IS NULL, 0, 1) AS has_transaction_90d
FROM `kkbox-churn-analytics.kkbox.cohort_sample` AS c
LEFT JOIN features AS f
  ON c.msno = f.msno;

SELECT
  COUNT(*) AS total_users,
  COUNT(DISTINCT msno) AS unique_users,
  SUM(is_churn) AS churned_users,
  COUNTIF(has_transaction_90d = 0) AS users_without_transactions,
  SUM(transaction_rows_90d) AS total_transaction_rows
FROM `kkbox-churn-analytics.kkbox.user_transaction_features`;
