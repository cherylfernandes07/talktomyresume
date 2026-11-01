# Talk to My Resume

> Upload a resume. Ask it anything.

**Talk to My Resume** is an AI-native recruiter tool that turns a static PDF into a conversational interface. Instead of skimming a resume line by line, recruiters upload it and ask natural questions — the app answers instantly, grounded entirely in the candidate's own words.

---

## How It Works

1. Recruiter uploads a candidate's PDF resume
2. The app parses and chunks the resume text
3. Chunks are embedded and stored in an in-memory vector store
4. Recruiter asks questions in plain English
5. The app retrieves relevant chunks and generates grounded answers
6. Session ends — nothing is stored, nothing persists

No candidate data is retained after the session closes.

---

## Supported Sources

Recruiters can build a fuller picture of a candidate by combining multiple sources in one session:

| Source | How to add |
|---|---|
| **PDF resume** | File upload |
| **Cover letter** | File upload (second PDF) |
| **Writing sample** | File upload |
| **LinkedIn profile** | Paste URL |
| **GitHub profile** | Paste URL |
| **Portfolio website** | Paste URL |

All sources are chunked, embedded, and queried together. Answers cite which source they came from — *"Based on her GitHub profile..."* — so recruiters know exactly where the information came from.

---

## Example Questions

- *"Does this candidate have team lead experience?"*
- *"How many years of Python does she have?"*
- *"Would she be a good fit for a staff engineer role?"*
- *"Has she worked at a startup before?"*
- *"What's her strongest technical skill?"*

---

## Stack

| Layer | Technology |
|---|---|
| **Frontend / Chat UI** | LibreChat (cloned + customized) |
| **Backend** | FastAPI (Python) |
| **PDF parsing** | PyMuPDF |
| **Embeddings** | Sentence Transformers (local) |
| **Vector store** | pgvector (PostgreSQL) |
| **LLM** | Groq (cloud) or HuggingFace Inference API |
| **Orchestration** | Strands Agents |

---

## Architecture

```
Recruiter uploads PDF
        │
        ▼
FastAPI /upload endpoint
  ├── PyMuPDF extracts text
  ├── Text is chunked (500 chars, 50 char overlap)
  ├── Chunks embedded via Sentence Transformers
  └── Stored in pgvector (PostgreSQL)
        │
        ▼
Recruiter asks a question (via LibreChat)
        │
        ▼
FastAPI /chat endpoint
  ├── Question embedded
  ├── Top-k chunks retrieved from pgvector
  ├── Chunks + question sent to Groq or HuggingFace
  └── Grounded answer returned
        │
        ▼
Recruiter reads answer
```

---

## Local Setup

### Prerequisites

- Docker
- Python 3.11+
- Node.js 20+
- A [Groq API key](https://console.groq.com) — free, no credit card required (key starts with `gsk_`)
- A [HuggingFace token](https://huggingface.co/settings/tokens) — free account works (token starts with `hf_`)

### 1. Add your API keys

Create `backend/.env`:

```
GROQ_API_KEY=gsk_your_key_here
HF_TOKEN=hf_your_token_here
```

### 2. Clone and start LibreChat + vectordb

```bash
cd ~/talktomyresume/librechat
docker compose up -d
```

### 3. Start the FastAPI backend

```bash
cd ~/talktomyresume/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

### 4. Open the app

```
http://localhost:3080
```

Upload a PDF resume and start asking questions.

---

## Quick Test — Groq

Want to verify everything is working end to end? Follow these steps after completing Local Setup above.

**1. Upload a resume:**
```bash
curl -X POST http://localhost:8080/upload \
  -F "file=@/path/to/your/resume.pdf"
```

Expected response:
```json
{"chunks_stored": 13}
```

**2. Ask a question:**
```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this candidates most recent job?", "provider": "groq"}'
```

Expected response:
```json
{"answer": "Their most recent role is..."}
```

---

## Quick Test — HuggingFace

Same steps, just swap the provider:

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What programming languages does this candidate know?", "provider": "huggingface"}'
```

> ⚠️ See Known Issues below — HuggingFace is currently returning 401 errors.

---

## Project Structure

```
talk-to-my-resume/
├── backend/
│   ├── main.py           # FastAPI app — /upload, /chat, /v1/chat/completions
│   ├── requirements.txt
│   ├── .env              # GROQ_API_KEY and HF_TOKEN (not committed)
│   └── tests/
│       └── test_api.py   # pytest test suite
├── librechat/
│   ├── docker-compose.yml
│   └── librechat.yaml    # Endpoint config — Groq + Resume RAG
└── README.md
```

---

## Run Tests

```bash
cd ~/talktomyresume/backend
pytest tests/test_api.py -v
```

---

## Design Decisions

**Why pgvector instead of FAISS in-memory?**
pgvector persists embeddings across server restarts and sessions. Resumes uploaded once stay queryable without re-uploading. For a truly ephemeral session, swap back to FAISS.

**Why Groq?**
Fast inference, generous free tier, no local GPU required. The Qwen models available on Groq perform well for Q&A against short context windows like resume chunks.

**Why LibreChat?**
Battle-tested chat UI with file upload support, streaming responses, and conversation history — without building a frontend from scratch.

**Why FastAPI?**
Python-native, fits naturally with Sentence Transformers and pgvector. Same language as the ML toolchain.

---

## Privacy

- Resumes are chunked and stored in a local PostgreSQL database (not sent to any third party)
- Questions and context are sent to Groq or HuggingFace for inference only
- No candidate data is logged or retained by the LLM providers beyond their standard API terms

---

## Known Issues

### HuggingFace — 401 Unauthorized

The HuggingFace provider is wired up in `main.py` but currently returns a 401 error when calling the Inference API. The token loads correctly from `.env` (verified via the `/whoami` endpoint), but authentication is still failing.

To reproduce:
```bash
curl -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/whoami
```

**Workaround:** Use `"provider": "groq"` in all `/chat` requests until this is resolved.

---

## Roadmap

- [ ] Additional sources — LinkedIn, GitHub, portfolio URLs scraped and embedded alongside the resume
- [ ] Multi-resume upload — screen several candidates side by side
- [ ] Fit scoring — score a candidate against a job description
- [ ] Fix HuggingFace 401 — enable provider toggle in production
- [ ] Bedrock / Claude Haiku — swap Groq for cloud inference on deploy
- [ ] Fine-tuned ResumeDecider — small classifier for fast yes/no skill questions

---

## Built by

[Nirvaan Labs](https://nirvaanlabs.com) · Cheryl Fernandes