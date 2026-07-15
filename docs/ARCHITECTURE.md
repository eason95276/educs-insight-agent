# EduCS Insight Agent Architecture

## Data Flow

```text
CSV / Excel
  -> data validation
  -> Pandas metrics
  -> SQLite query tools
  -> privacy masking
  -> token-budgeted summary
  -> DeepSeek report generation
  -> local LLM response cache
```

## LangGraph Workflow

The V3 agent uses LangGraph to wrap the deterministic tool router:

```text
route_intent
  -> execute_tool
  -> prepare_response
```

The router supports:

- monthly_report
- rate_drop_diagnosis
- product_school_ranking
- acceptance_status
- group_workload
- knowledge_rag

Each route calls explicit tools and produces an execution trace. This is intentionally more controllable than letting an LLM directly inspect raw tables.

## RAG Scope

RAG is used for semi-structured knowledge:

- business metric rules
- privacy and token strategy
- diagnosis playbooks
- historical monthly notes

Structured metrics still use Pandas and SQL.

Implementation details:

- LangChain Core `Document` is used as the document abstraction.
- Markdown files are split by headings and paragraph length.
- The default embedding is a local 384-dimension hash embedding to avoid model download and privacy leakage.
- Retrieval uses Chroma persistent vector storage under `data/chroma`, then applies keyword-overlap reranking. If Chroma is unavailable, retrieval falls back to keyword matching.
- Retrieved chunks are reranked with a lightweight keyword-overlap score.

## Interview Point

The project separates responsibilities:

- Pandas/SQL: reliable calculation
- LangChain Core: prompt templates and document abstraction
- RAG: retrieve business context
- Agent: route tasks and call tools
- LLM: generate readable reports and explanations
- Cache: avoid repeated LLM calls for identical report payloads
