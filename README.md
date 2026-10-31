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
| **Vector store** | In-memory (FAISS) |
| **LLM** | Ollama (Mistral 7B, runs locally) |
| **Orchestration** | Strands Agents |

---

## Architecture

```
Recruiter uploads PDF
        │
        ▼
FastAPI /upload endpoint
  ├── PyMuPDF extracts text
  ├── Text is chunked (500 tokens, 50 token overlap)
  ├── Chunks embedded via Sentence Transformers
  └── Stored in FAISS in-memory vector store
        │
        ▼
Recruiter asks a question (via LibreChat)
        │
        ▼
FastAPI /chat endpoint
  ├── Question embedded
  ├── Top-k chunks retrieved from FAISS
  ├── Chunks + question sent to Ollama (Mistral 7B)
  └── Grounded answer returned
        │
        ▼
Recruiter reads answer
```

---

## Local Setup

### Prerequisites

- Docker
- [Ollama](https://ollama.ai) installed on your Mac
- Python 3.11+
- Node.js 20+

### 1. Pull the local model

```bash
ollama pull mistral
```

### 2. Clone and start LibreChat

```bash
git clone https://github.com/danny-avila/LibreChat.git
cd LibreChat
cp .env.example .env
# Edit .env — point LLM endpoint to your FastAPI backend
docker compose up
```

### 3. Start the FastAPI backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Open the app

```
http://localhost:3080
```

Upload a PDF resume and start asking questions.

---

## Project Structure

```
talk-to-my-resume/
├── backend/
│   ├── main.py           # FastAPI app — /upload and /chat endpoints
│   ├── parser.py         # PDF text extraction (PyMuPDF)
│   ├── chunker.py        # Text chunking with overlap
│   ├── embedder.py       # Sentence Transformers embeddings
│   ├── store.py          # FAISS in-memory vector store
│   ├── agent.py          # Strands agent — tool orchestration
│   └── requirements.txt
├── LibreChat/            # Cloned and customized chat frontend
└── README.md
```

---

## Design Decisions

**Why in-memory vector store?**
For MVP, sessions are ephemeral — nothing is stored when the tab closes. FAISS in-memory is fast, requires no infrastructure, and keeps candidate data private by design.

**Why Ollama + Mistral locally?**
Zero API costs during development. When ready to deploy, swap `ollama` for Bedrock (Claude Haiku) or HuggingFace Inference API with a one-line config change.

**Why LibreChat?**
Battle-tested chat UI with file upload support, streaming responses, and conversation history — without building a frontend from scratch.

**Why FastAPI?**
Python-native, fits naturally with PyMuPDF, FAISS, and Sentence Transformers. Same language as the ML toolchain.

---

## Privacy

- Resumes are never written to disk or a database
- All processing happens in memory for the duration of the session
- Closing the browser tab clears all session data
- No candidate data is shared with third-party services (all inference runs locally via Ollama)

---

## Roadmap

- [ ] Additional sources — LinkedIn, GitHub, portfolio URLs scraped and embedded alongside the resume
- [ ] Multi-resume upload — screen several candidates side by side
- [ ] Fit scoring — score a candidate against a job description
- [ ] Pinecone persistence — optional session save for returning recruiters
- [ ] Bedrock / Claude Haiku — swap Ollama for cloud inference on deploy
- [ ] Fine-tuned ResumeDecider — small classifier for fast yes/no skill questions

---

## Built by

[Nirvaan Labs](https://nirvaanlabs.com) · Cheryl Fernandes