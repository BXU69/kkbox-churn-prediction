WITH duplicate_days AS (
    SELECT
        msno,
        log_day,
        COUNT(*) AS records_per_day
    FROM read_parquet(?, hive_partitioning = true)
    WHERE cohort = ?
    GROUP BY msno, log_day
    HAVING COUNT(*) > 1
)
SELECT
    COUNT(*) AS duplicate_user_days,
    COALESCE(
        SUM(records_per_day), 0
    ) AS rows_in_duplicate_days,
    COALESCE(
        SUM(records_per_day - 1), 0
    ) AS excess_rows,
    COALESCE(
        MAX(records_per_day), 0
    ) AS max_records_per_duplicate_day
FROM duplicate_days
