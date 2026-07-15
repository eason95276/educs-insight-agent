SELECT
    st.group_name,
    st.staff_name,
    COUNT(p.project_id) AS project_count,
    SUM(CASE WHEN p.status = '已验收' THEN 1 ELSE 0 END) AS accepted_count,
    SUM(CASE WHEN p.status = '未启动' THEN 1 ELSE 0 END) AS not_started_count
FROM staff st
LEFT JOIN projects p ON st.staff_id = p.staff_id
WHERE st.group_name = ?
GROUP BY st.group_name, st.staff_name
ORDER BY project_count DESC
