WITH parsed AS (
    SELECT
        msno,
        TRY_STRPTIME("date", '%Y%m%d')::DATE AS log_day,
        TRY_CAST(num_25 AS BIGINT) AS num_25,
TRY_CAST(num_50 AS BIGINT) AS num_50,
TRY_CAST(num_75 AS BIGINT) AS num_75,
TRY_CAST(num_985 AS BIGINT) AS num_985,
TRY_CAST(num_100 AS BIGINT) AS num_100,
TRY_CAST(num_unq AS BIGINT) AS num_unq,
        TRY_CAST(total_secs AS DOUBLE) AS listening_seconds
    FROM read_csv(?, all_varchar = true)
)
SELECT
    COUNT(*) AS rows,
    MIN(log_day) AS first_log_date,
    MAX(log_day) AS last_log_date,
    COUNT(*) FILTER (
        WHERE msno IS NULL OR TRIM(msno) = ''
    ) AS missing_user_ids,
    COUNT(*) FILTER (
        WHERE log_day IS NULL
    ) AS missing_or_invalid_dates,
    COUNT(*) FILTER (
        WHERE num_25 IS NULL OR num_50 IS NULL OR num_75 IS NULL OR num_985 IS NULL OR num_100 IS NULL OR num_unq IS NULL
    ) AS rows_with_missing_or_invalid_counts,
    COUNT(*) FILTER (
        WHERE num_25 < 0 OR num_50 < 0 OR num_75 < 0 OR num_985 < 0 OR num_100 < 0 OR num_unq < 0
    ) AS rows_with_negative_counts,
    COUNT(*) FILTER (
        WHERE listening_seconds IS NULL
           OR NOT ISFINITE(listening_seconds)
    ) AS rows_with_missing_or_invalid_seconds,
    COUNT(*) FILTER (
        WHERE ISFINITE(listening_seconds)
          AND listening_seconds < 0
    ) AS rows_with_negative_seconds,
    COUNT(*) FILTER (
        WHERE listening_seconds = 0
    ) AS rows_with_zero_seconds,
    COUNT(*) FILTER (
        WHERE ISFINITE(listening_seconds)
          AND listening_seconds > 86400
    ) AS rows_above_24_hours,
    MIN(listening_seconds) FILTER (
        WHERE ISFINITE(listening_seconds)
    ) AS min_finite_seconds,
    MAX(listening_seconds) FILTER (
        WHERE ISFINITE(listening_seconds)
    ) AS max_finite_seconds
FROM parsed
