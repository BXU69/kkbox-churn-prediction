WITH history AS (
    SELECT *
    FROM read_csv(?, all_varchar = true)
    WHERE TRY_STRPTIME(transaction_date, '%Y%m%d')::DATE
          <= CAST(? AS DATE)
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY msno
            ORDER BY
                transaction_date DESC,
                (
                    plan_list_price
                    || payment_plan_days
                    || payment_method_id
                ) ASC,
                is_cancel DESC,
                CASE
                    WHEN is_cancel = '1'
                    THEN membership_expire_date
                END ASC,
                CASE
                    WHEN is_cancel = '0'
                    THEN membership_expire_date
                END DESC
        ) AS row_rank
    FROM history
)
SELECT
    msno,
    TRY_STRPTIME(
        transaction_date, '%Y%m%d'
    )::DATE AS last_transaction_day,
    TRY_STRPTIME(
        membership_expire_date, '%Y%m%d'
    )::DATE AS candidate_expiration
FROM ranked
WHERE row_rank = 1
  AND TRY_STRPTIME(membership_expire_date, '%Y%m%d')::DATE
      BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
