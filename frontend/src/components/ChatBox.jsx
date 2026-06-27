import { useState, useRef, useEffect } from "react"

const API = "http://localhost:8000"

export default function ChatBox() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! I've loaded the video. Ask me anything about it — or try 'summarise the key points' or 'what was discussed at the start?'" }
  ])
  const [input, setInput]     = useState("")
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || thinking) return

    const userMessage = input.trim()
    setInput("")
    setThinking(true)

    // Add user message immediately
    setMessages(prev => [...prev, { role: "user", content: userMessage }])
    // Add empty assistant message for streaming
    setMessages(prev => [...prev, { role: "assistant", content: "" }])

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      // Stream tokens into the last assistant message
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const token = decoder.decode(value)
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: "assistant",
            content: updated[updated.length - 1].content + token
          }
          return updated
        })
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: "assistant",
          content: "❌ Error connecting to backend."
        }
        return updated
      })
    } finally {
      setThinking(false)
    }
  }

  const clearChat = async () => {
    await fetch(`${API}/clear`, { method: "POST" })
    setMessages([{ role: "assistant", content: "Chat cleared! Ask me anything about the video." }])
  }

  return (
    <div className="chatbox">
      <div className="chat-header">
        <span>Chat</span>
        <button className="clear-btn" onClick={clearChat}>🗑 Clear</button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <span className="message-role">{msg.role === "user" ? "You" : "VidMind"}</span>
            <p className="message-content">{msg.content}</p>
          </div>
        ))}
        {thinking && (
          <div className="message assistant">
            <span className="message-role">VidMind</span>
            <p className="message-content thinking">Thinking…</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          className="chat-input"
          type="text"
          placeholder="Ask something about the video…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          disabled={thinking}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={thinking || !input.trim()}
        >
          Send ➤
        </button>
      </div>
    </div>
  )
}