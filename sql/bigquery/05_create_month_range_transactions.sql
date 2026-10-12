-- Sandbox-compatible partition demonstration for historical source dates.
-- month_index: 0 = Dec 2016, 1 = Jan 2017, 2 = Feb 2017.
-- Integer-range partitions do not have time-based partition expiration;
-- the sandbox's table-level expiration still applies.
CREATE TABLE `kkbox-churn-analytics.kkbox.transactions_month_partitioned`
PARTITION BY RANGE_BUCKET(month_index, GENERATE_ARRAY(0, 3, 1))
CLUSTER BY msno
OPTIONS (require_partition_filter = TRUE)
AS
WITH parsed AS (
  SELECT
    msno,
    payment_method_id,
    payment_plan_days,
    plan_list_price,
    actual_amount_paid,
    is_auto_renew,
    SAFE.PARSE_DATE('%Y%m%d', CAST(transaction_date AS STRING))
      AS transaction_day,
    SAFE.PARSE_DATE('%Y%m%d', CAST(membership_expire_date AS STRING))
      AS membership_expire_day,
    is_cancel
  FROM `kkbox-churn-analytics.kkbox.transactions_sample`
)
SELECT
  *,
  DATE_DIFF(transaction_day, DATE '2016-12-01', MONTH) AS month_index
FROM parsed;

SELECT
  COUNT(*) AS transaction_rows,
  COUNT(DISTINCT msno) AS users_with_transactions,
  MIN(transaction_day) AS first_transaction_date,
  MAX(transaction_day) AS last_transaction_date
FROM `kkbox-churn-analytics.kkbox.transactions_month_partitioned`
WHERE month_index BETWEEN 0 AND 2;
