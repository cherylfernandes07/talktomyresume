from dotenv import load_dotenv
load_dotenv()


from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import psycopg2
from psycopg2.extras import execute_values
from groq import Groq
from huggingface_hub import InferenceClient
import io
import os
import time
import json
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB connection
DB = {
    "host": "localhost",
    "database": "mydatabase",
    "user": "myuser",
    "password": "mypassword",
    "port": 5432,
}

# Models
embedder = SentenceTransformer("all-MiniLM-L6-v2")
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
hf_client = InferenceClient(
    # model="mistralai/Mistral-7B-Instruct-v0.3",
    model="Qwen/Qwen2.5-7B-Instruct",
    token=os.environ["HF_TOKEN"]
)

def get_conn():
    return psycopg2.connect(**DB)

def setup_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resume_chunks (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding vector(384)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

setup_db()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    reader = PdfReader(io.BytesIO(contents))
    text = "\n".join(page.extract_text() for page in reader.pages)

    # Chunk by paragraph
    # chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 50]

    # Chunk by character with overlap
    chunk_size = 500
    chunk_overlap = 50
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
        start += chunk_size - chunk_overlap    

    # Embed
    embeddings = embedder.encode(chunks).tolist()

    # Store
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM resume_chunks;")  # clear old resume
    execute_values(cur,
        "INSERT INTO resume_chunks (content, embedding) VALUES %s",
        [(chunks[i], embeddings[i]) for i in range(len(chunks))]
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"chunks_stored": len(chunks)}

@app.post("/chat")
async def chat(body: dict):
    question = body["question"]
    provider = body.get("provider", "groq")
    print("DEBUG body:", json.dumps(body, indent=2))
    
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    def extract_content(m):
        c = m["content"]
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
        return ""

    question = next((extract_content(m) for m in reversed(messages) if m["role"] == "user"), "")

    # Embed question
    q_embedding = embedder.encode(question).tolist()

    # Retrieve top 3 chunks
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT content FROM resume_chunks
        ORDER BY embedding <-> %s::vector
        LIMIT 3;
    """, (q_embedding,))
    chunks = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    context = "\n\n".join(chunks)
    answer = call_llm(question, context, provider)
    return {"answer": answer}

@app.post("/v1/chat/completions")
async def openai_chat(body: dict):
    print("DEBUG body:", json.dumps(body, indent=2))
    
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    def extract_content(m):
        c = m["content"]
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return " ".join(p.get("text", "") for p in c if isinstance(p, dict))
        return ""

    question = next((extract_content(m) for m in reversed(messages) if m["role"] == "user"), "")

    # Embed question
    q_embedding = embedder.encode(question).tolist()

    # Retrieve top 3 chunks
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT content FROM resume_chunks
        ORDER BY embedding <-> %s::vector
        LIMIT 3;
    """, (q_embedding,))
    chunks = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    context = "\n\n".join(chunks)
    
    provider = body.get("provider", "groq")
    answer = call_llm(question, context, provider)

    print("*** DEBUG answer:", answer)

    if stream:
        def generate():
            chunk = {
                "id": "chatcmpl-resume",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "resume-rag",
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": answer},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            done = {
                "id": "chatcmpl-resume",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "resume-rag",
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(done)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    return {
        "id": "chatcmpl-resume",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "resume-rag",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": answer},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }

def call_llm(question: str, context: str, provider: str = "groq") -> str:
    messages = [
        {"role": "user", "content": f"You answer questions about a resume. Use only the context provided. Be concise.\n\nContext:\n{context}\n\nQuestion: {question}"}
    ]
    
    if provider == "groq":
        response = groq_client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            max_tokens=500,
            messages=messages
        )
    else:
        response = hf_client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            # model="mistralai/Mistral-7B-Instruct-v0.3",
            # model="meta-llama/Meta-Llama-3.1-8B-Instruct",
            max_tokens=500,
            messages=messages
        )
    
    return response.choices[0].message.content