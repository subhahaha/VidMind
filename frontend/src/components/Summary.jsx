import { useState } from "react"

export default function Summary({ summary }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="summary-card">
      <div className="summary-header">
        <span className="summary-title">Video Summary</span>
        <button
          className="collapse-btn"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? "Show ▾" : "Hide ▴"}
        </button>
      </div>
      {!collapsed && (
        <div className="summary-body">
          {summary.split("\n").map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      )}
    </div>
  )
}