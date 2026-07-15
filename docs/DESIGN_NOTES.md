# Design Notes

## Project Scope

EduCS Insight Agent is designed for customer-success analytics in an AI education product scenario. The system focuses on repeatable operational workflows:

- product usage analysis across schools
- delivery project status tracking
- training qualification diagnosis
- natural-language data queries
- monthly report generation
- exam-score import template cleaning

The project uses simulated and anonymized data so that the full workflow can run locally without exposing real customer or student information.

## Agent Boundary

The system does not treat the LLM as a spreadsheet calculator. Structured metrics are computed locally with Pandas, SQL, and deterministic rules. The LLM is only used after the system has prepared compact, privacy-masked context.

This separation keeps the system easier to verify:

- Pandas handles metric calculation and data cleaning.
- SQL handles structured query tasks.
- RAG retrieves semi-structured business rules and diagnosis context.
- DeepSeek generates readable report drafts from aggregated summaries.
- LangGraph exposes the workflow as explicit nodes and transitions.

## RAG Scope

RAG is used for semi-structured knowledge that is difficult to encode as SQL tables, including:

- training qualification policy
- risk diagnosis playbook
- privacy and token policy
- historical monthly notes

The RAG module uses LangChain Core `Document`, Markdown chunking, local hash embeddings, persistent Chroma vector retrieval under `data/chroma`, and keyword-overlap reranking. If Chroma is unavailable, the system falls back to keyword retrieval so the application remains runnable.

## Privacy And Cost Controls

The project avoids sending raw tables to the LLM. Instead, it computes rankings, rates, deltas, diagnosis signals, and short RAG snippets locally, then sends only the final compact context to the model.

Sensitive fields such as school names, customer success staff names, student names, and student IDs are masked before they enter LLM context. API keys are loaded from `.env` and excluded from version control.

## Workflow Design

The natural-language query workflow is implemented with LangGraph:

```text
route_intent
  -> execute_tool
  -> prepare_response
```

This structure makes the application easier to extend. New query types can be added by introducing new intent rules, SQL files, Pandas tools, or RAG knowledge documents without rewriting the entire app.

