WITH ordered AS (
    SELECT
        t.*,
        TRY_STRPTIME(
            t.transaction_date, '%Y%m%d'
        )::DATE AS transaction_day,
        TRY_STRPTIME(
            t.membership_expire_date, '%Y%m%d'
        )::DATE AS expiration_day,
        ROW_NUMBER() OVER (
            PARTITION BY t.msno
            ORDER BY
                t.transaction_date ASC,
                (
                    t.plan_list_price
                    || t.payment_plan_days
                    || t.payment_method_id
                ) DESC,
                t.is_cancel ASC,
                CASE
                    WHEN t.is_cancel = '1'
                    THEN t.membership_expire_date
                END DESC,
                CASE
                    WHEN t.is_cancel = '0'
                    THEN t.membership_expire_date
                END ASC
        ) AS event_order
    FROM future_transactions AS t
    INNER JOIN label_candidates AS c
        ON t.msno = c.msno
    WHERE TRY_STRPTIME(t.transaction_date, '%Y%m%d')::DATE
          > CAST(? AS DATE)
      AND TRY_STRPTIME(t.transaction_date, '%Y%m%d')::DATE
          <= CAST(? AS DATE)
),
first_renewal AS (
    SELECT
        msno,
        transaction_day AS renewal_day,
        event_order
    FROM ordered
    WHERE is_cancel = '0'
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY msno ORDER BY event_order
    ) = 1
),
adjusted AS (
    SELECT
        c.msno,
        c.candidate_expiration,
        r.renewal_day,
        LEAST(
            c.candidate_expiration,
            COALESCE(
                MIN(o.expiration_day) FILTER (
                    WHERE o.is_cancel = '1'
                      AND (
                          r.event_order IS NULL
                          OR o.event_order < r.event_order
                      )
                ),
                c.candidate_expiration
            )
        ) AS adjusted_expiration
    FROM label_candidates AS c
    LEFT JOIN first_renewal AS r
        ON c.msno = r.msno
    LEFT JOIN ordered AS o
        ON c.msno = o.msno
    GROUP BY
        c.msno,
        c.candidate_expiration,
        r.renewal_day,
        r.event_order
),
gaps AS (
    SELECT
        *,
        DATE_DIFF(
            'day',
            adjusted_expiration,
            renewal_day
        ) AS renewal_gap_days
    FROM adjusted
)
SELECT
    *,
    CASE
        WHEN renewal_day IS NULL THEN 1
        WHEN renewal_gap_days >= 30 THEN 1
        ELSE 0
    END AS is_churn
FROM gaps
