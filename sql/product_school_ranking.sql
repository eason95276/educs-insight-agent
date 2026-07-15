SELECT
    s.school_name,
    s.school_type,
    u.product_name,
    ROUND(AVG(1.0 * u.teacher_active / NULLIF(u.teacher_total, 0)), 4) AS teacher_usage_rate,
    ROUND(AVG(1.0 * u.student_active / NULLIF(u.student_total, 0)), 4) AS student_usage_rate,
    ROUND(AVG(
        (1.0 * u.teacher_active / NULLIF(u.teacher_total, 0)
        + 1.0 * u.student_active / NULLIF(u.student_total, 0)) / 2
    ), 4) AS combined_usage_rate
FROM usage u
JOIN schools s ON u.school_id = s.school_id
WHERE u.month = ? AND u.product_name = ?
GROUP BY s.school_id, s.school_name, s.school_type, u.product_name
ORDER BY combined_usage_rate DESC
LIMIT 10
