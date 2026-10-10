SELECT
    COUNT(*) AS label_users,
    COUNT(m.msno) AS matched_users,
    COUNT(*) - COUNT(m.msno) AS unmatched_users,
    ROUND(
        100.0 * COUNT(m.msno) / COUNT(*), 2
    ) AS matched_pct
FROM labels_v2 AS l
LEFT JOIN members_raw AS m
    ON l.msno = m.msno;
