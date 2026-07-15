SELECT
    st.staff_name,
    st.group_name,
    p.status,
    COUNT(*) AS project_count
FROM projects p
JOIN staff st ON p.staff_id = st.staff_id
WHERE st.staff_name = ?
GROUP BY st.staff_name, st.group_name, p.status
ORDER BY project_count DESC
