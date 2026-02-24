# YouTube RAG — Chat with any YouTube Video

A production-grade Retrieval-Augmented Generation (RAG) application that lets you
ask questions about any YouTube video using **local AI models** via Ollama.

## Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.10+** | Backend runtime |
| **Ollama** running locally | `http://localhost:11434` |
| **Models pulled** | `ollama pull tinyllama` • `ollama pull phi3:mini` • `ollama pull nomic-embed-text` |

## Quick Start

```bash
# 1. Navigate to the backend
cd youtube-rag/backend

# 2. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python run.py
```

Open **http://localhost:8000** in your browser.

## Usage

1. Enter a **YouTube Video ID** in the sidebar (e.g. `dQw4w9WgXcQ`).
2. Click the **load** button — the transcript is fetched, chunked, and indexed.
3. Choose a **model** (tinyllama or phi3:mini).
4. **Ask questions** in the chat — answers come from the video transcript only.

## Project Structure

```
youtube-rag/
├── backend/
│   ├── app/
│   │   ├── config.py            # Settings (Ollama URL, models, defaults)
│   │   ├── main.py              # FastAPI entry point
│   │   ├── routers/rag.py       # API endpoints
│   │   └── services/
│   │       ├── transcript.py    # YouTube transcript fetcher
│   │       ├── rag_pipeline.py  # Embed → FAISS → Retrieve → Generate
│   │       └── models.py        # Ollama model listing
│   ├── requirements.txt
│   └── run.py                   # Uvicorn launcher
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── README.md
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET`  | `/api/health`     | Health check |
| `GET`  | `/api/models`     | List available Ollama models |
| `POST` | `/api/transcript` | Load & index a YouTube transcript |
| `POST` | `/api/ask`        | Ask a question (RAG pipeline) |

## Tech Stack

- **Backend**: FastAPI · LangChain · FAISS · Ollama
- **Frontend**: Vanilla HTML/CSS/JS
- **Embedding**: nomic-embed-text (local)
- **LLMs**: tinyllama · phi3:mini (local via Ollama)
