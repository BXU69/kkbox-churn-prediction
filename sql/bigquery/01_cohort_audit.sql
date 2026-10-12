-- Project ID is an example; replace it when reproducing in another project.
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT msno) AS unique_users,
  COUNTIF(msno IS NULL OR TRIM(msno) = '') AS missing_user_ids,
  COUNTIF(is_churn IS NULL OR is_churn NOT IN (0, 1)) AS invalid_labels,
  COUNTIF(is_churn = 1) AS churned_users,
  ROUND(AVG(is_churn) * 100, 2) AS churn_rate_pct
FROM `kkbox-churn-analytics.kkbox.cohort_sample`;
