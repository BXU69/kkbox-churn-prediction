-- Historical date partitions may immediately expire under the sandbox's
-- 60-day partition retention. Verify counts before feature engineering.
SELECT
  (SELECT COUNT(*)
   FROM `kkbox-churn-analytics.kkbox.transactions_sample`)
    AS source_rows,
  (SELECT COUNT(*)
   FROM `kkbox-churn-analytics.kkbox.transactions_partitioned`
   WHERE transaction_day BETWEEN DATE '2016-12-01' AND DATE '2017-02-28')
    AS partitioned_rows;
