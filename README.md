# VidMind — YouTube Video Chat

A full-stack AI app that lets you paste any YouTube URL and have a real conversation about the video — with automatic summarisation and streaming responses.

Built with **FastAPI + React**, powered by **Ollama (llama3.2)** running locally — free, private, no API costs.

---



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
Split into character-based chunks (1000 chars, 200 overlap)
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

##  Project structure

```
vidmind/
├── backend/
│   ├── main.py              # FastAPI server + API endpoints
│   ├── rag_engine.py         # RAG logic (transcript → chunks → FAISS → Ollama)
│   ├── memory.py             # SQLite persistent chat memory
│   ├── evaluate.py            # LLM-as-a-judge evaluation script
│   ├── evaluate_ragas.py      # RAGAS evaluation script (Groq-powered)
│   ├── .env.example           # API key template
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── App.jsx            # Main app + theme toggle
    │   ├── index.css          # Dark/light theme styles
    │   └── components/
    │       ├── UrlInput.jsx   # YouTube URL input
    │       ├── Summary.jsx    # Auto summary panel
    │       └── ChatBox.jsx    # Streaming chat interface
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

##  Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) installed

### Step 1 — Install Ollama and pull the model
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

##  Evaluation

VidMind includes two separate evaluation approaches to measure RAG answer quality.

### 1 — LLM-as-a-judge (`evaluate.py`)

A second LLM scores each answer 1-5 based on accuracy, specificity, and relevance.

```
cd backend
python evaluate.py --url "https://youtube.com/watch?v=YOUR_VIDEO_ID"
```

### 2 — RAGAS framework (`evaluate_ragas.py`)

Measures 4 RAG-specific metrics using [Groq](https://groq.com) as the fast judge model.

```
pip install ragas==0.1.21 datasets langchain-community==0.2.19 langchain-core==0.2.43 langchain-groq==0.1.9 python-dotenv
```

Create a `.env` file in the backend folder (see `.env.example`):
```
GROQ_API_KEY=your_groq_api_key_here
```

Then run:
```
python evaluate_ragas.py --url "https://youtube.com/watch?v=YOUR_VIDEO_ID"
```

### Best recorded RAGAS scores

| Metric | Score | Meaning |
|---|---|---|
| **Faithfulness** | **0.914** | Answers are grounded in the transcript — very low hallucination |
| **Context Utilization** | **0.810** | Retrieved chunks are effectively used in answers |
| **Context Recall** | **0.312** | FAISS retrieves ~31% of truly relevant sections — main weakness |
| **Overall** | **0.679 — Good ** | |

> Note: RAGAS scores vary ±0.2 between runs due to LLM non-determinism and
> free-tier timeout variance. Scores above represent the best recorded evaluation run.

### What the scores mean

**Faithfulness 0.914** is the most important metric — it means the model almost never makes up information. It only answers from what it retrieved.

**Context Recall 0.312** is the main weakness — FAISS misses about 69% of the truly relevant transcript sections per question. This is a retrieval coverage problem, not a generation problem.

---

## What I learned building this

- **Full-stack AI architecture** — connecting a React frontend to a FastAPI backend with a RAG pipeline
- **REST API design** — building endpoints with FastAPI, request/response models with Pydantic, CORS configuration
- **Streaming over HTTP** — using `StreamingResponse` in FastAPI and `ReadableStream` in React to stream tokens live
- **YouTube transcript processing** — fetching and parsing captions with timestamps using youtube-transcript-api
- **Component-based React** — building a multi-component UI with state management and theme toggling
- **RAG evaluation** — implementing both LLM-as-a-judge and RAGAS, understanding their tradeoffs on local vs cloud infrastructure
- **Debugging LLM behavior** — diagnosing chunking issues, hallucination, and inference speed bottlenecks on CPU-only hardware
- **Infrastructure tradeoffs** — RAGAS requires fast cloud LLMs for evaluation; local CPU models cause timeout failures due to call volume

---

## Future improvements

### RAG Quality
- **Cross-encoder reranker** — retrieve 12 chunks with FAISS, rerank with `cross-encoder/ms-marco-MiniLM-L-6-v2`, keep top 6. Would directly improve context recall (currently 0.312). Requires smaller chunks to stay within LLM token limits
- **HyDE retrieval** — generate a hypothetical answer first, embed that instead of the raw question. Finds more semantically relevant chunks since the hypothetical answer uses vocabulary closer to the transcript
- **Chapter-aware chunking** — split transcript by video chapters instead of fixed character windows, preserving topic boundaries

### Evaluation
- **Fix answer_relevancy metric** — currently times out due to RAGAS's parallel job runner hitting the free Groq tier limit (6000 TPM). Needs a higher API tier or sequential evaluation mode
- **Upgrade Groq tier** — free tier causes rate limit errors with large contexts, preventing reranker evaluation

### Features
- Support multiple videos at once
- Export chat as structured notes (markdown/PDF)
- Deploy frontend to Vercel + backend to Render
- Add support for non-English videos

---

## Limitations

- Only works with YouTube videos that have captions/subtitles enabled
- Runs on CPU — responses may be slower on lower-end machines
- Free Ollama models are less capable than paid APIs (GPT-4, Claude)
- RAGAS evaluation requires a Groq API key (free) and may have occasional timeouts on the free tier