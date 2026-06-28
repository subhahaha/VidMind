# VidMind — YouTube Video Chat

A full-stack AI app that lets you paste any YouTube URL and have a real conversation about the video — with automatic summarisation and streaming responses.

Built with **FastAPI + React**, powered by **Ollama (llama3.2)** running locally — free, private, no API costs.

---

## Demo

![VidMind Demo](demo.gif)

---

## Features

- Paste any YouTube URL and load it instantly
- **Auto summary** — key points generated automatically when video loads
- **Streaming chat** — answers appear word by word like ChatGPT
- **Timestamp references** — answers tell you where in the video to look
- **Conversation memory** — understands follow-up questions
- **Persistent chat history** — saved to SQLite across sessions
- **Dark / Light theme toggle**
- **100% local & free** — no API keys, no data leaves your machine

---

## How it works

```
YouTube URL
      │
      ▼
Extract transcript (youtube-transcript-api)
      │
      ▼
Split into sentence-aware chunks
      │
      ▼
Embed chunks (all-MiniLM-L6-v2) → store in FAISS index
      │
      ├──► Auto-generate structured summary (Ollama)
      │
      └──► Chat is unlocked
                │
                ▼
        User asks question
                │
                ▼
        Embed question → search FAISS → retrieve top-6 chunks
                │
                ▼
        Build prompt (summary + history + context + question)
                │
                ▼
        Stream response from Ollama (llama3.2)
                │
                ▼
        Answer appears live in React chat UI + saved to SQLite
```

---

## Tech stack

| Layer | Tool | Role |
|---|---|---|
| Frontend | React + Vite | Chat UI with dark/light theme |
| Backend | FastAPI | REST API server |
| LLM | Ollama (llama3.2) | Generates answers locally |
| Embeddings | all-MiniLM-L6-v2 | Converts text to vectors |
| Vector search | FAISS | Finds relevant transcript chunks |
| Transcript | youtube-transcript-api | Fetches YouTube captions |
| Memory | SQLite | Persists chat history |

---

## Project structure

```
vidmind/
├── backend/
│   ├── main.py          # FastAPI server + API endpoints
│   ├── rag_engine.py    # RAG logic (transcript → chunks → FAISS → Ollama)
│   ├── memory.py        # SQLite persistent chat memory
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── App.jsx           # Main app + theme toggle
    │   ├── index.css         # Dark/light theme styles
    │   └── components/
    │       ├── UrlInput.jsx  # YouTube URL input
    │       ├── Summary.jsx   # Auto summary panel
    │       └── ChatBox.jsx   # Streaming chat interface
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) installed

### Step 1 — Install Ollama and pull the model
Download Ollama from https://ollama.com, then run:
```
ollama pull llama3.2
```
Ollama starts automatically in the background after install.

### Step 2 — Backend setup
```
cd vidmind/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```
Backend runs on **http://localhost:8000**

### Step 3 — Frontend setup
Open a second terminal:
```
cd vidmind/frontend
npm install
npm run dev
```
Frontend runs on **http://localhost:5173**

---

## Usage

1. Open **http://localhost:5173**
2. Paste any YouTube URL with captions
3. Wait for the video to load and the summary to appear
4. Start chatting!

### Example questions to try
- *What is this video about?*
- *Summarise the key points*
- *What was discussed at the beginning?*
- *Explain [concept] mentioned in simple terms*
- *What examples were given?*
- *What are the key takeaways?*

---

## What I learned building this

- **Full-stack AI architecture** — connecting a React frontend to a FastAPI backend with a RAG pipeline
- **REST API design** — building endpoints with FastAPI, request/response models with Pydantic, CORS configuration
- **Streaming over HTTP** — using `StreamingResponse` in FastAPI and `ReadableStream` in React to stream tokens live
- **YouTube transcript processing** — fetching and parsing captions with timestamps using youtube-transcript-api
- **Component-based React** — building a multi-component UI with state management and theme toggling
- **RAG pipeline** — same core skills as DocMind (chunking, FAISS, embeddings) applied to a new data source

---

## Future improvements

- Support for multiple videos at once
- Chapter-aware chunking (split by video chapters)
- Export chat as PDF or markdown notes
- Deploy frontend to Vercel + backend to Render
- Add support for non-English videos

---

## Limitations

- Only works with YouTube videos that have captions/subtitles enabled
- Runs on CPU — responses may be slower on lower-end machines
- Free Ollama models are less capable than paid APIs (GPT-4, Claude)