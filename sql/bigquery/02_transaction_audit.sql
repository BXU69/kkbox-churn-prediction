-- Current source table name after reimport: transactions_sample.
WITH parsed AS (
  SELECT
    msno,
    SAFE.PARSE_DATE('%Y%m%d', CAST(transaction_date AS STRING))
      AS transaction_day
  FROM `kkbox-churn-analytics.kkbox.transactions_sample`
)
SELECT
  COUNT(*) AS transaction_rows,
  COUNT(DISTINCT t.msno) AS users_with_transactions,
  MIN(t.transaction_day) AS first_transaction_date,
  MAX(t.transaction_day) AS last_transaction_date,
  COUNTIF(t.transaction_day IS NULL) AS invalid_transaction_dates,
  COUNTIF(t.transaction_day < DATE '2016-12-01'
    OR t.transaction_day > DATE '2017-02-28') AS outside_window_rows,
  COUNTIF(c.msno IS NULL) AS unmatched_transaction_rows
FROM parsed AS t
LEFT JOIN `kkbox-churn-analytics.kkbox.cohort_sample` AS c
  ON t.msno = c.msno;
