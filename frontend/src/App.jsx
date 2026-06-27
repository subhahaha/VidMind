import { useState } from "react"
import UrlInput from "./components/UrlInput"
import Summary from "./components/Summary"
import ChatBox from "./components/ChatBox"
import "./index.css"

export default function App() {
  const [theme, setTheme]       = useState("dark")
  const [videoLoaded, setVideoLoaded] = useState(false)
  const [summary, setSummary]   = useState("")
  const [loading, setLoading]   = useState(false)
  const [status, setStatus]     = useState("")

  const handleVideoLoaded = (summaryText) => {
    setVideoLoaded(true)
    setSummary(summaryText)
  }

  return (
    <div className={`app ${theme}`}>

      {/* ── Header ── */}
      <header className="header">
        <div className="header-left">
          <span className="logo">🎬 VidMind</span>
          <span className="tagline">Chat with any YouTube video</span>
        </div>
        <button
          className="theme-toggle"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
        </button>
      </header>

      {/* ── URL Input ── */}
      <UrlInput
        onVideoLoaded={handleVideoLoaded}
        setLoading={setLoading}
        setStatus={setStatus}
        loading={loading}
      />

      {/* ── Status message ── */}
      {status && <p className="status-msg">{status}</p>}

      {/* ── Main content (summary + chat) ── */}
      {videoLoaded && (
        <div className="main-content">
          <Summary summary={summary} />
          <ChatBox />
        </div>
      )}

      {/* ── Empty state ── */}
      {!videoLoaded && !loading && (
        <div className="empty-state">
          <p>Paste a YouTube URL above to get started</p>
          <p className="empty-hint">Works with lectures, podcasts, tutorials, talks — any video with captions</p>
        </div>
      )}

    </div>
  )
}