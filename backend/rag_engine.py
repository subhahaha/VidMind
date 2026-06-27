"""
rag_engine.py — Core RAG logic for VidMind
YouTube transcript → chunks → embeddings → FAISS index
Query + history → top-k chunks → Ollama → streaming answer
"""

import re
import json
import numpy as np
import faiss
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from sentence_transformers import SentenceTransformer

# ── Config ──────────────────────────────────────────────────────
OLLAMA_URL    = "http://localhost:11434/api/generate"
OLLAMA_MODEL  = "llama3.2"
EMBED_MODEL   = "all-MiniLM-L6-v2"
CHUNK_SIZE    = 600
CHUNK_OVERLAP = 150
TOP_K         = 6


class RAGEngine:
    def __init__(self):
        print("Loading embedding model…")
        self.embedder    = SentenceTransformer(EMBED_MODEL, local_files_only=True)
        self.index       = None
        self.chunks      = []
        self.video_title = ""
        self.doc_summary = ""

    # ── Load video transcript ─────────────────────────────────────
    def load_video(self, video_id: str, title: str = "") -> int:
        transcript = self._fetch_transcript(video_id)
        self.video_title = title or video_id
        self.chunks = self._split(transcript)
        self._build_index()
        self.doc_summary = self._summarise()
        return len(self.chunks)

    def is_ready(self) -> bool:
        return self.index is not None and len(self.chunks) > 0

    def get_summary(self) -> str:
        return self.doc_summary

    # ── Query pipeline (streaming) ────────────────────────────────
    def query_stream(self, question: str, history: list = []):
        search_query = self._build_search_query(question, history)
        context = self._retrieve(search_query)
        yield from self._generate_stream(question, context, history)

    # ── Internals ─────────────────────────────────────────────────
    def _fetch_transcript(self, video_id: str) -> str:
        """Fetch transcript from YouTube and join into plain text with timestamps."""
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id)
        lines = []
        for entry in transcript:
            mins = int(entry.start) // 60
            secs = int(entry.start) % 60
            lines.append(f"[{mins}:{secs:02d}] {entry.text}")
        return " ".join(lines)

    def _split(self, text: str) -> list[str]:
        """Sentence-aware chunker."""
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks, current = [], ""
        for sentence in sentences:
            if len(current) + len(sentence) <= CHUNK_SIZE:
                current += " " + sentence
            else:
                if current:
                    chunks.append(current.strip())
                overlap_start = max(0, len(current) - CHUNK_OVERLAP)
                current = current[overlap_start:] + " " + sentence
        if current:
            chunks.append(current.strip())
        return chunks

    def _build_index(self):
        embeddings = self.embedder.encode(self.chunks, show_progress_bar=True)
        embeddings = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    def _build_search_query(self, question: str, history: list) -> str:
        if not history:
            return question
        user_messages = [m["content"] for m in history if m["role"] == "user"]
        if user_messages:
            return f"{user_messages[-1]} {question}"
        return question

    def _retrieve(self, query: str) -> str:
        q_emb = self.embedder.encode([query], show_progress_bar=False)
        q_emb = np.array(q_emb, dtype="float32")
        faiss.normalize_L2(q_emb)
        _, indices = self.index.search(q_emb, TOP_K)
        retrieved = [self.chunks[i] for i in indices[0] if i < len(self.chunks)]
        return "\n\n---\n\n".join(retrieved)

    def _summarise(self) -> str:
        """Generate a structured summary of the whole video."""
        # Use first 2000 chars as overview snippet
        snippet = " ".join(self.chunks[:5])[:2000]
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"""You are summarising a YouTube video transcript.

Generate a structured summary with:
- A one-line overview of what the video is about
- 4-6 key points covered (as bullet points)
- Any important terms or concepts mentioned

TRANSCRIPT SNIPPET:
{snippet}

SUMMARY:""",
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 400}
        }
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=120)
            return r.json().get("response", "").strip()
        except:
            return "Summary unavailable."

    def _build_history_text(self, history: list) -> str:
        if not history:
            return ""
        lines = []
        for msg in history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _generate_stream(self, question: str, context: str, history: list):
        history_text = self._build_history_text(history)
        history_section = f"CONVERSATION HISTORY:\n{history_text}\n\n" if history_text else ""
        summary_section = f"VIDEO OVERVIEW:\n{self.doc_summary}\n\n" if self.doc_summary else ""

        prompt = f"""You are a smart assistant helping a user understand a YouTube video they loaded.
The transcript includes timestamps like [1:23] — reference them when relevant so the user knows where to look.

RULES:
- Answer based only on the VIDEO CONTEXT below
- Follow the user's instruction exactly
- Use CONVERSATION HISTORY to understand follow-up questions
- Be concise, clear, and friendly
- If something isn't in the video, say so honestly
- Reference timestamps when helpful e.g. "This is discussed around [4:32]"

{summary_section}{history_section}VIDEO CONTEXT (most relevant sections):
{context}

User: {question}
Assistant:"""

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": 600,
                "top_p": 0.9,
            }
        }

        try:
            with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=180) as r:
                r.raise_for_status()
                full_text = ""
                for line in r.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            full_text += token
                            if "User:" in full_text or "\nUser" in full_text:
                                break
                            yield token
                        if chunk.get("done", False):
                            break
        except requests.exceptions.ConnectionError:
            yield "Could not connect to Ollama. Make sure it is running."
        except Exception as e:
            yield f"Error: {e}"