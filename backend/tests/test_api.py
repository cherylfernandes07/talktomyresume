import pytest
import requests

BASE_URL = "http://localhost:8080"

def test_chat_returns_answer():
    response = requests.post(f"{BASE_URL}/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "What is Cheryls most recent job?"}],
        "provider": "groq"
    })
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"][0]["message"]["content"]) > 0

def test_chat_answer_is_relevant():
    response = requests.post(f"{BASE_URL}/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "What programming languages does Cheryl know?"}],
        "provider": "groq"
    })
    assert response.status_code == 200
    answer = response.json()["choices"][0]["message"]["content"].lower()
    assert any(lang in answer for lang in ["python", "typescript", "javascript"])

def test_upload_rejects_empty_file():
    response = requests.post(f"{BASE_URL}/upload", files={
        "file": ("empty.pdf", b"", "application/pdf")
    })
    assert response.status_code == 500