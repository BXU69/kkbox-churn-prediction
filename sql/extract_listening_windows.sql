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
        TRY_CAST(total_secs AS DOUBLE) AS total_secs_raw
    FROM read_csv(?, all_varchar = true)
)
SELECT
    w.cohort,
    p.msno,
    p.log_day,
    p.num_25, p.num_50, p.num_75, p.num_985, p.num_100, p.num_unq,
    p.total_secs_raw,
    CASE
        WHEN ISFINITE(p.total_secs_raw)
         AND p.total_secs_raw BETWEEN 0 AND 86400
        THEN p.total_secs_raw
        ELSE NULL
    END AS total_secs_clean,
    CASE
        WHEN ISFINITE(p.total_secs_raw)
         AND p.total_secs_raw BETWEEN 0 AND 86400
        THEN 0
        ELSE 1
    END AS duration_anomaly
FROM parsed AS p
INNER JOIN required_windows AS w
    ON p.msno = w.msno
   AND p.log_day BETWEEN w.window_start AND w.window_end
