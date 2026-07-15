# Rate Drop Diagnosis Playbook

When a customer success staff member or delivery group has a qualification rate drop, check these factors:

1. Data freshness: whether usage data has not been updated for more than 7 days.
2. Sample size: whether the number of training projects changed significantly.
3. Observation window: whether projects were just trained and usage data has not accumulated.
4. School type mix: whether market schools increased in the current month.
5. Product mix: whether low-usage products account for a larger share.

The LLM should not guess the reason directly. It should call tools first, then summarize verified signals.
