WITH parsed AS (
    SELECT
        t.msno,
        TRY_STRPTIME(
            t.transaction_date, '%Y%m%d'
        )::DATE AS transaction_day,
        TRY_CAST(t.payment_plan_days AS INTEGER) AS plan_days,
        TRY_CAST(t.is_auto_renew AS INTEGER) AS auto_renew,
        TRY_CAST(t.is_cancel AS INTEGER) AS cancel_flag
    FROM read_csv(?, all_varchar = true) AS t
    INNER JOIN cohort_users AS c
        ON t.msno = c.msno
),
windowed AS (
    SELECT *
    FROM parsed
    WHERE transaction_day BETWEEN CAST(? AS DATE)
                              AND CAST(? AS DATE)
)
SELECT
    msno,
    COUNT(*) AS transaction_rows_90d,
    COUNT(DISTINCT transaction_day) AS transaction_days_90d,
    COUNT(*) FILTER (
        WHERE cancel_flag = 1
    ) AS cancel_rows_90d,
    AVG(auto_renew) AS auto_renew_share_90d,
    AVG(plan_days) AS avg_plan_days_90d,
    DATE_DIFF(
        'day',
        MAX(transaction_day),
        CAST(? AS DATE)
    ) AS days_since_last_transaction_90d
FROM windowed
GROUP BY msno
