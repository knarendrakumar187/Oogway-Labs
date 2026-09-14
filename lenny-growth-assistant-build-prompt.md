# Master Build Prompt — "The Lenny Growth Assistant" (FDE Take-Home)

Paste this whole document into Claude Code / Cursor / Codex as the first instruction. It's written in phases so the agent builds a working demo first, then adds polish only if time allows.

---

## Context for the agent

You are acting as a Forward Deployed Engineer. Build "The Lenny Growth Assistant" per the attached assignment brief (paste the full brief text here too, or point the agent at the file). This is a take-home with a **hard deadline in ~24 hours**, so ruthlessly prioritize a working end-to-end system over completeness. Ship something that runs cleanly with one command, even if scope is trimmed — a smaller working product beats a larger broken one.

Work in phases. After each phase, run the app, fix what's broken, and commit before moving on. Do not start Phase 2 until Phase 1 actually runs end-to-end.

---

## Phase 0 — Scope lock (do this first, ~10 min)

Before writing code, write `PRD.md` with:
- Primary user: a PM/growth practitioner who wants grounded answers from Lenny's Podcast without reading transcripts themselves.
- Success metric: e.g. "% of answers with a verifiable source citation" and "time to first answer."
- Assumptions: transcript set will be a curated subset (~15–25 episodes, not the full archive) due to time constraints — state this explicitly as a scope cut, not hidden.
- Explicit exclusions: no auth/multi-tenant, no transcript auto-refresh pipeline, no fine-tuning, single Ollama model only (not several).
- Risks: hallucination, local-model quality vs Claude/GPT, cost of no citation grounding, XSS risk in HTML artifact rendering, latency of local models.

## Phase 1 — MVP (must work, this is the demo)

1. **Backend (FastAPI)**
   - `/chat` endpoint: takes session_id + message, returns grounded answer + sources.
   - `/sessions` endpoints: create/list/get session history.
   - `/health` endpoint.
   - Pydantic request/response models, structured error responses (no bare 500s).

2. **Persistence (PostgreSQL)**
   - Tables: `sessions`, `messages`, `sources_cited`. Use SQLAlchemy or SQLModel + Alembic migrations.
   - Use Docker Compose Postgres locally (don't require Supabase/Railway sign-up for the reviewer).

3. **Knowledge base / RAG**
   - Ingest 15–25 Lenny's Podcast transcripts (pick a small curated set — document which ones and why).
   - Chunk (e.g. 500–800 tokens, overlap ~100), embed (local sentence-transformers model to avoid API cost, or OpenAI/Claude embeddings if a key is available), store in a simple vector store (pgvector in the same Postgres instance, or Chroma/FAISS locally — pgvector is preferred since it avoids a second moving part).
   - Every answer must include which transcript(s)/timestamp ranges it drew from. If retrieval returns nothing relevant, the assistant must say so rather than guessing.

4. **LLM provider toggle**
   - Config layer (env var, e.g. `LLM_PROVIDER=ollama|anthropic|openai`) read at request time, no code changes needed to switch.
   - Ollama is mandatory and must be the default for the submitted demo — pick a small model that runs on a laptop (e.g. `llama3.1:8b` or `qwen2.5:7b`).
   - Cloud provider (Claude or OpenAI) as the alternate path, with graceful fallback/error message if no key is set (never crash the app).
   - Show the active provider in the UI.

5. **Ship 30 for 30 skill**
   - A distinct tool/function (not a one-off prompt) that takes a grounded answer and rewrites it as a ~1,250-word essay: strong hook, headings/bullets/bold, one concrete takeaway, claims traceable to transcript sources.
   - Encode the actual Ship 30 for 30 principles (brief, skim the linked guide first) as a short rubric inside the skill's system prompt, not vibes.

6. **Frontend (minimal but real)**
   - Simple chat UI (React or plain HTML/JS — don't over-engineer given the timeline) with session list, message history, provider indicator.
   - Artifact Viewer panel beside the chat: renders Markdown directly; renders HTML/CSS inside a **sandboxed iframe** (`sandbox="allow-same-origin"` only if needed, no `allow-scripts` unless you implement real sanitization — default to blocking scripts). Document exactly what's allowed/blocked and why in `architecture.md`.

## Phase 2 — Operational readiness (do this once Phase 1 runs)

- `docker-compose.yml` for Postgres + backend + (optionally) frontend, one-command startup.
- `.env.example` with every required/optional var and safe defaults, no real secrets.
- Structured logging (retrieval hits/misses, provider used, latency, DB errors) — plain `logging` module is fine, doesn't need to be fancy.
- Handle gracefully: missing API key, Ollama not running, empty retrieval, DB connection failure — all should degrade to a clear user-facing message, never a stack trace.
- `README.md`: architecture overview, prerequisites, install, env vars, run commands, how to run tests, troubleshooting.
- `architecture.md`: schema, endpoints, ingestion/retrieval flow, agent routing, model toggle, security notes, deployment topology diagram (ASCII is fine).
- `design.md`: UI/UX principles, key states (empty, loading, error, streaming), responsive behavior, accessibility notes, and what you deliberately simplified.
- Tests: a handful of meaningful pytest tests (retrieval returns expected chunk for a known query, session persistence round-trips, provider fallback triggers correctly) — not exhaustive coverage, just prove the critical paths work. Short manual UI test plan as a markdown checklist.
- `agent-transcripts/` folder: export/save the actual coding session logs (including at least one place you had to correct the agent), strip secrets.

## Phase 3 — Only if time remains

- More transcripts, streaming responses, nicer UI polish, additional automated tests, better observability (e.g. request IDs).

## Constraints to hold throughout

- Never fabricate a source citation — if the retriever didn't return it, don't cite it.
- Never commit `.env`, API keys, or DB credentials.
- Every reviewer-facing doc should read like it was written by someone handing off a real system, not padded to look thorough — be direct about what's cut and why (that's explicitly part of the evaluation criteria).

## After the agent finishes each phase, ask it to:

1. Actually run the app and paste the output/errors back to you rather than assuming it works.
2. List anything from the brief it did NOT implement, with a one-line reason, so you can decide whether to fix it or document it as a scope cut in the PRD.
