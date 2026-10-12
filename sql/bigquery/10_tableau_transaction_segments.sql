-- Mutually exclusive user segments from the fixed 10,000-user sample.
-- Behavior associations do not measure an intervention effect.
-- In Tableau, use SUM(churned_users) / SUM(users) after regrouping.
WITH segments AS (
  SELECT
    *,
    CASE
      WHEN has_transaction_90d = 0 THEN '04_No transactions'
      WHEN days_since_last_transaction_90d <= 7 THEN '01_0-7 days'
      WHEN days_since_last_transaction_90d <= 30 THEN '02_8-30 days'
      ELSE '03_31-90 days'
    END AS recency_segment,
    CASE
      WHEN has_transaction_90d = 0 THEN '04_No transactions'
      WHEN auto_renew_share_90d = 1 THEN '01_All auto-renew'
      WHEN auto_renew_share_90d = 0 THEN '03_No auto-renew'
      ELSE '02_Mixed auto-renew'
    END AS auto_renew_segment
  FROM `kkbox-churn-analytics.kkbox.user_transaction_features`
)
SELECT
  recency_segment,
  auto_renew_segment,
  COUNT(*) AS users,
  SUM(is_churn) AS churned_users,
  SUM(transaction_rows_90d) AS transaction_rows,
  ROUND(AVG(is_churn), 6) AS churn_rate
FROM segments
GROUP BY recency_segment, auto_renew_segment
ORDER BY recency_segment, auto_renew_segment;
