"""
main.py — FastAPI backend for VidMind
Endpoints:
  POST /load-video   — load a YouTube video by URL
  GET  /summary      — get the auto-generated summary
  POST /chat         — chat with the video (streaming)
  POST /clear        — clear chat history
"""

import re
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag_engine import RAGEngine
from memory import ChatMemory

app = FastAPI(title="VidMind API")

# ── CORS — allows React frontend to talk to this backend ─────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── State ────────────────────────────────────────────────────────
rag    = RAGEngine()
memory = ChatMemory()
SESSION_ID = str(uuid.uuid4())[:8]


# ── Request models ───────────────────────────────────────────────
class VideoRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    message: str


# ── Helpers ──────────────────────────────────────────────────────
def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"embed\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Could not extract video ID from URL")


# ── Endpoints ────────────────────────────────────────────────────
@app.post("/load-video")
async def load_video(req: VideoRequest):
    """Load a YouTube video — fetch transcript, build FAISS index, generate summary."""
    try:
        video_id = extract_video_id(req.url)
        num_chunks = rag.load_video(video_id)
        memory.clear_session(SESSION_ID)  # fresh chat for each new video
        return {
            "status": "success",
            "video_id": video_id,
            "chunks": num_chunks,
            "message": f"Video loaded — {num_chunks} chunks indexed."
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load video: {e}")


@app.get("/summary")
async def get_summary():
    """Return the auto-generated video summary."""
    if not rag.is_ready():
        raise HTTPException(status_code=400, detail="No video loaded yet.")
    return {"summary": rag.get_summary()}


@app.post("/chat")
async def chat(req: ChatRequest):
    """Stream a response to the user's question about the video."""
    if not rag.is_ready():
        raise HTTPException(status_code=400, detail="No video loaded yet.")

    history = memory.load_history(SESSION_ID)
    memory.save_message(SESSION_ID, "user", req.message)

    full_response = []

    def generate():
        for token in rag.query_stream(req.message, history):
            full_response.append(token)
            yield token
        # Save complete response after streaming finishes
        memory.save_message(SESSION_ID, "assistant", "".join(full_response))

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/clear")
async def clear_chat():
    """Clear the chat history for the current session."""
    memory.clear_session(SESSION_ID)
    return {"status": "cleared"}


@app.get("/health")
async def health():
    return {"status": "ok", "video_loaded": rag.is_ready()}