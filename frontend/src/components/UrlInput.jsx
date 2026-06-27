import { useState } from "react"
import axios from "axios"

const API = "http://localhost:8000"

export default function UrlInput({ onVideoLoaded, setLoading, setStatus, loading }) {
  const [url, setUrl] = useState("")

  const handleLoad = async () => {
    if (!url.trim()) return
    setLoading(true)
    setStatus("Loading video transcript…")

    try {
      // Step 1 — load video + build FAISS index
      await axios.post(`${API}/load-video`, { url })
      setStatus("Generating summary…")

      // Step 2 — fetch auto summary
      const summaryRes = await axios.get(`${API}/summary`)
      setStatus("Video loaded! Ask anything below.")
      onVideoLoaded(summaryRes.data.summary)
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to load video."
      setStatus(`${msg}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="url-input-row">
      <input
        className="url-input"
        type="text"
        placeholder="Paste a YouTube URL here…  e.g. https://youtube.com/watch?v=..."
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleLoad()}
        disabled={loading}
      />
      <button
        className="load-btn"
        onClick={handleLoad}
        disabled={loading || !url.trim()}
      >
        {loading ? "Loading…" : "Load Video"}
      </button>
    </div>
  )
}