-- Historical experiment: DO NOT use this table for the sandbox workflow.
-- The sandbox's 60-day partition retention expired the 2016-2017 data.
-- Use 05_create_month_range_transactions.sql in the working pipeline.
-- A plain CREATE TABLE prevents accidentally replacing an existing table.
CREATE TABLE `kkbox-churn-analytics.kkbox.transactions_partitioned`
PARTITION BY transaction_day
CLUSTER BY msno
OPTIONS (
  require_partition_filter = TRUE,
  description = 'Sample transactions partitioned by transaction date and clustered by user ID'
)
AS
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
FROM `kkbox-churn-analytics.kkbox.transactions_sample`;
