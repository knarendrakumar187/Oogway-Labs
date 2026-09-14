# 🦉 Oogway Labs — Lenny Growth Assistant

> A RAG-powered AI chat assistant grounded in 18 curated Lenny's Podcast episodes, with an integrated **Ship 30 for 30** essay-generation skill.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green?logo=fastapi) ![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Grounded chat** | Answers sourced from 573 indexed chunks across 18 Lenny episodes |
| **Citations** | Every response links back to speaker, episode, and timestamp |
| **Multi-provider LLM** | Switch between Groq (fast free cloud), Ollama (local), OpenAI, Anthropic, or Mock (no key needed) |
| **Ship 30 for 30 skill** | Transforms any grounded answer into a publish-ready atomic essay |
| **Session history** | Persistent conversation sessions stored in SQLite (or PostgreSQL) |
| **Zero-config start** | Mock provider works out-of-the-box — no API keys required |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Browser UI                         │
│          frontend/ (HTML + CSS + JS)                  │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP / REST
┌────────────────────▼─────────────────────────────────┐
│              FastAPI Backend  :8000                   │
│  ┌──────────┐  ┌────────────┐  ┌───────────────────┐ │
│  │ RAG      │  │ LLM Router │  │ Ship30 Skill      │ │
│  │ (cosine) │  │ Groq /     │  │ (essay generator) │ │
│  │ 573 chks │  │ Ollama /   │  │                   │ │
│  └──────────┘  │ OpenAI /   │  └───────────────────┘ │
│                │ Anthropic /│                         │
│                │ Mock       │                         │
│                └────────────┘                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │  SQLAlchemy ORM  →  SQLite (default) / Postgres  │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | 24+ | Required for containerised run |
| [Python](https://www.python.org/) | 3.11+ | Required for local / test run |
| [Ollama](https://ollama.com/) | latest | **Optional** — for local LLM inference |

---

### Option A — Docker Compose (recommended)

```bash
# 1. Clone the repository
git clone https://github.com/knarendrakumar187/Oogway-Labs.git
cd Oogway-Labs

# 2. Copy and (optionally) edit environment variables
cp .env.example .env

# 3. Build and start
docker compose up --build
```

Open **http://localhost:8000** — the UI will be served automatically.

> **First run note**: On startup the backend auto-generates `data/chunks.json` (573 chunks)
> by downloading and embedding 18 Lenny episode transcripts. This takes ~2 min on first launch.

---

### Option B — Local Python (no Docker)

```bash
# 1. Clone and enter
git clone https://github.com/knarendrakumar187/Oogway-Labs.git
cd Oogway-Labs

# 2. Create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env        # edit as needed

# 5. (One-time) Download transcripts & build knowledge base
python scripts/fetch_transcripts.py
python scripts/ingest.py

# 6. Start the API server
uvicorn backend.app.main:app --reload --port 8000
```

Open **http://localhost:8000**.

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and adjust as needed:

```env
# LLM Provider: groq | mock | ollama | openai | anthropic
LLM_PROVIDER=groq

# Groq (fast cloud inference — recommended for zero local setup)
GROQ_API_KEY=gsk_...
GROQ_MODEL=groq/compound-mini

# Ollama (local model — optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# OpenAI (optional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Database (SQLite auto-used if Postgres unavailable)
DATABASE_URL=postgresql://lenny:growth@localhost:5432/lenny_growth

# RAG tuning
SIMILARITY_THRESHOLD=0.35
TOP_K_CHUNKS=5
```

> **No API keys needed**: The `mock` provider generates deterministic responses and works completely offline.

---

## 🦙 Using Ollama (optional)

To use a local model instead of the mock provider:

```bash
# 1. Install Ollama from https://ollama.com/
# 2. Pull a model
ollama pull llama3.1:8b

# 3. In .env, set:
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# 4. Restart the server / containers
```

---

## 🧪 Running Tests

```bash
# Activate your virtual environment first, then:
python -m pytest tests/ -v
```

Tests cover:
- Health endpoint
- Session lifecycle (create / list / detail / delete)
- Grounded chat with source citations
- Ungrounded query handling
- Ship 30 for 30 essay transformation
- Graceful LLM provider error (503 response)

---

## 📁 Project Structure

```
Oogway-Labs/
├── backend/
│   └── app/
│       ├── api/endpoints.py      # REST routes
│       ├── services/
│       │   ├── rag.py            # Vector similarity search
│       │   ├── llm.py            # LLM provider routing
│       │   └── ship30.py         # Ship 30 essay skill
│       ├── config.py             # Settings (pydantic-settings)
│       ├── database.py           # SQLAlchemy engine + fallback
│       ├── models.py             # ORM models
│       ├── schemas.py            # Pydantic request/response schemas
│       └── main.py               # FastAPI app entry point
├── frontend/
│   ├── index.html                # UI layout
│   ├── style.css                 # Styling
│   └── app.js                    # UI logic
├── scripts/
│   ├── fetch_transcripts.py      # Download 18 episode transcripts
│   └── ingest.py                 # Chunk, embed, save chunks.json
├── tests/
│   └── test_api.py               # Pytest test suite
├── data/                         # Auto-generated (transcripts + chunks.json)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── PRD.md                        # Product Requirements Document
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check + provider status |
| `POST` | `/api/chat` | Send a message, get grounded response |
| `POST` | `/api/chat/ship30` | Transform answer → Ship 30 essay |
| `GET` | `/api/sessions` | List all sessions |
| `POST` | `/api/sessions` | Create a new session |
| `GET` | `/api/sessions/{id}` | Get session with full message history |
| `DELETE` | `/api/sessions/{id}` | Delete a session |

### Example Chat Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What did Elena Verna say about PLG tactics?",
    "provider": "mock"
  }'
```

---

## 🗺️ Roadmap

- [ ] pgvector integration for scalable vector search
- [ ] Streaming LLM responses (SSE)
- [ ] User authentication & multi-tenant sessions
- [ ] Additional podcast episode ingestion pipeline
- [ ] Slack / Discord bot integration

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- [Lenny's Podcast](https://www.lennyspodcast.com/) — episode content
- [FastAPI](https://fastapi.tiangolo.com/) — backend framework
- [Sentence Transformers](https://www.sbert.net/) — embeddings (`all-MiniLM-L6-v2`)
- [Ship 30 for 30](https://www.ship30for30.com/) — atomic essay methodology
