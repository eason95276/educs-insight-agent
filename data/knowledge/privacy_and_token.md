# Privacy And Token Strategy

The system does not send raw school, teacher, student, or staff records to the LLM.

Structured data is first processed locally:

- Pandas calculates usage rate, qualification rate, rankings, and diagnostics.
- SQLite supports structured query tools.
- Sensitive fields are masked before LLM context construction.
- Only aggregated summaries are sent to DeepSeek.

This reduces token cost, latency, and privacy risk.

Sensitive fields:

- school_name
- staff_name
- student name
- student id
