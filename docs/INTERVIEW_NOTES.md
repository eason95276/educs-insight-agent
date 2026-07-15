# Interview Notes

## One-Minute Project Pitch

EduCS Insight Agent is an AI education customer success analytics agent based on my internship scenario. It analyzes product usage, project delivery status, customer success training qualification rates, and exam-score import data.

The key design is that raw structured data is not directly sent to the LLM. Pandas and SQLite first compute reliable metrics, then the agent sends only privacy-masked aggregated summaries to DeepSeek for report generation.

## Why This Is An Agent

It is not a simple Excel summarizer. The system uses a LangGraph workflow to classify the user's business question, select tools, run deterministic calculations, retrieve relevant business knowledge, and return an answer with an execution trace.

## Why Use RAG

RAG is used for business rules, diagnosis playbooks, historical notes, and privacy/token policies. Structured metrics such as qualification rate and product usage rate are computed with Pandas/SQL instead of vector search.

## Token Optimization

The app does not send full tables to the model. It sends compact summaries such as rankings, rates, deltas, and diagnosis signals.

## Privacy Protection

Sensitive fields such as school names, customer success staff names, student names, and student IDs are masked before entering LLM context.

## Strong Resume Bullet

Built an AI education customer success analytics agent with Python, Streamlit, Pandas, SQLite, LangChain Core, LangGraph, RAG, and DeepSeek API. The system supports product usage analysis, delivery status tracking, training qualification diagnosis, monthly report generation, and exam-score template cleaning. Designed privacy masking and token-saving context compression so that raw education data is processed locally and only aggregated summaries are sent to the LLM.

## Interview Q&A

### Q: What is the difference between this project and directly using ChatGPT or Codex?

Directly using ChatGPT is a one-off interaction. This project productizes the workflow: data validation, SQL/Pandas metrics, RAG retrieval, privacy masking, token compression, caching, and report generation are built into a repeatable system.

### Q: Why not send the whole Excel file to the LLM?

Because structured metrics should be deterministic and verifiable. Sending full tables increases token cost, latency, and privacy risk. The project computes metrics locally and sends only compact summaries to the LLM.

### Q: Where is RAG used?

RAG is used for semi-structured knowledge such as training qualification rules, privacy/token policies, diagnosis playbooks, and historical monthly notes. Structured data still uses Pandas and SQL.

The RAG module uses LangChain Core `Document`, Markdown chunking, local hash embedding, persistent Chroma vector retrieval under `data/chroma`, and keyword-overlap reranking. If Chroma is unavailable, it falls back to keyword retrieval so the demo remains runnable.

### Q: Why LangGraph?

LangGraph makes the workflow explicit: route intent, execute tool, package answer. This is easier to trace and extend than a black-box prompt-only agent.
