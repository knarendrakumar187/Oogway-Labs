# Product Requirements Document (PRD)
# Project: The Lenny Growth Assistant (FDE Take-Home)

## 1. Executive Summary
"The Lenny Growth Assistant" is an AI-powered conversational assistant tailored for product managers, growth leads, and startup operators. It synthesizes grounded product and growth insights strictly from *Lenny's Podcast* transcripts, provides granular timestamped citations, transforms insights into publication-ready "Ship 30 for 30" essays, and previews outputs in a secure sandboxed artifact viewer.

---

## 2. Target User Persona
- **Primary User:** Product Managers, Growth Practitioners, and Founders who need rapid, credible, and grounded strategic advice (e.g. B2B PLG loops, marketplace liquidity, retention mechanics, pricing strategies) without manually combing through hundreds of hours of audio or raw transcript text.
- **Jobs to be Done (JTBD):**
  1. *Quick answers:* "What did Elena Verna say about B2B freemium vs. reverse trials?"
  2. *Deep framework retrieval:* Find exact quotes, context, and speaker philosophies.
  3. *Content synthesis:* Convert conversational insights into concise, structured memos or essays adhering to Ship 30 for 30 format.

---

## 3. Core Success Metrics
1. **Verifiable Source Citation Rate:** >= 95% of all answers must contain at least one verifiable episode, speaker, and timestamp attribution. If the knowledge base lacks relevant data, the assistant must explicitly state lack of knowledge rather than hallucinate.
2. **Zero Hallucinated Citations:** 0% fabricated episode titles or timestamps.
3. **Time to First Answer (TTFA):**
   - Cloud / Extractive: < 2.5 seconds.
   - Local Ollama (laptop inference): < 10 seconds.
4. **Single-Command Operability:** Reviewer can run the entire system via `docker compose up` or simple local scripts in under 2 minutes.

---

## 4. Key Assumptions & Scope Cuts
Due to the 24-hour evaluation timeline, the following deliberate scope trade-offs have been locked:
- **Curated Transcript Corpus (18 Episodes):** Rather than ingesting all 300+ episodes of Lenny's Podcast, the knowledge base indexes a curated collection of 18 landmark episodes covering core growth, product strategy, retention, pricing, and org design (e.g., Shreyas Doshi, Elena Verna, Casey Winters, Brian Balfour, Lenny Rachitsky, etc.).
- **Single-Model Configuration per Provider:** The assistant defaults to a single designated lightweight model for local execution (`llama3.1:8b` or `qwen2.5:7b` for Ollama) and standardized models for cloud (`claude-3-5-sonnet`, `gpt-4o-mini`). Dynamic multi-model routing or speculative decoding is excluded.
- **Local Fallback Mode:** To guarantee that reviewers without a GPU or pre-installed Ollama instance can immediately test and evaluate the entire UI, RAG retrieval, and session database, a high-fidelity local extractive synthesis engine (`mock` provider) is included alongside standard Ollama, Anthropic, and OpenAI adapters.

---

## 5. Explicit Exclusions (Non-Goals)
- **No Multi-tenancy or User Authentication:** The application operates in a single-workspace/local demo mode; no JWT, OAuth, or RBAC is required.
- **No Dynamic Ingestion Crawler:** Transcripts are pre-ingested into the vector store via an idempotent ingestion pipeline; there is no scheduled background scraper or YouTube RSS poller.
- **No Model Fine-Tuning:** Retrieval-Augmented Generation (RAG) with prompt-level rubrics is used exclusively.
- **No Unsandboxed Script Execution:** The frontend artifact viewer intentionally blocks arbitrary script execution inside generated HTML/CSS artifacts to eliminate XSS risks.

---

## 6. Technical Risks & Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Hallucination & Misattribution** | High | Retrieval guard threshold: if similarity score falls below cutoff, the system responds with an explicit boundary message ("I couldn't find any discussion of this in the indexed episodes") instead of improvising. |
| **Local Model Latency & Availability** | High | Provider abstraction layer (`LLM_PROVIDER`) dynamically selects between Ollama, OpenAI, Anthropic, and Extractive Fallback with friendly diagnostics instead of 500 error crashes. |
| **XSS via Generated Artifacts** | Critical | Dual-mode artifact renderer: Markdown is sanitized; HTML/CSS previews run inside a sandboxed iframe (`sandbox="allow-same-origin"`) with JavaScript execution strictly disabled. |
| **Database Dependency Overhead** | Medium | SQLAlchemy schema with dual-engine support: PostgreSQL + `pgvector` for Dockerized multi-container setups, and SQLite + vector indexing for zero-friction laptop test runs. |

---

## 7. Operational Deliverables
1. **FastAPI Backend:** `/api/chat`, `/api/chat/ship30`, `/api/sessions`, `/api/health`.
2. **Vector Store:** Chunked embeddings (500–800 tokens, 100 token overlap) with speaker and timestamp metadata.
3. **Ship 30 for 30 Skill:** Dedicated transformation engine converting grounded answers into ~1,250-word structured essays with clear hooks, bulleted frameworks, and concrete takeaways.
4. **Dual-Panel UI:** Clean, responsive chat interface with collapsible source drawers and an artifact preview panel.
5. **Operational Docker Stack:** `docker-compose.yml`, `.env.example`, automated pytest test suite, and operational documentation (`README.md`, `architecture.md`, `design.md`).
