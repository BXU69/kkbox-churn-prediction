WITH daily AS (
    SELECT
        l.*,
        w.cutoff,
        (
            l.num_25 + l.num_50 + l.num_75
            + l.num_985 + l.num_100
        ) AS song_plays
    FROM read_parquet(?, hive_partitioning = true) AS l
    INNER JOIN window_metadata AS w
        ON l.cohort = w.cohort
    WHERE l.cohort = ?
)
SELECT
    cohort,
    msno,
    COUNT(*) AS recorded_days_30d,
    SUM(song_plays) AS recorded_song_plays_30d,
    SUM(num_100) AS completed_song_plays_30d,
    SUM(num_unq) AS sum_daily_unique_songs_30d,
    SUM(total_secs_clean) AS valid_listening_seconds_30d,
    COUNT(total_secs_clean) AS valid_duration_days_30d,
    SUM(duration_anomaly) AS flagged_duration_days_30d,
    AVG(total_secs_clean) AS avg_seconds_per_valid_day_30d,
    SUM(num_100)::DOUBLE
        / NULLIF(SUM(song_plays), 0) AS completion_ratio_30d,
    DATE_DIFF(
        'day', MAX(log_day), MAX(cutoff)
    ) AS days_since_last_log_30d,
    COUNT(*) FILTER (
        WHERE log_day >= cutoff - INTERVAL '6 days'
    ) AS recorded_days_recent_7d,
    COUNT(*) FILTER (
        WHERE log_day BETWEEN cutoff - INTERVAL '13 days'
                          AND cutoff - INTERVAL '7 days'
    ) AS recorded_days_previous_7d,
    COALESCE(
        SUM(song_plays) FILTER (
            WHERE log_day >= cutoff - INTERVAL '6 days'
        ), 0
    ) AS recorded_plays_recent_7d,
    COALESCE(
        SUM(song_plays) FILTER (
            WHERE log_day BETWEEN cutoff - INTERVAL '13 days'
                              AND cutoff - INTERVAL '7 days'
        ), 0
    ) AS recorded_plays_previous_7d
FROM daily
GROUP BY cohort, msno
