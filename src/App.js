import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import axios from "axios";

const AGENTS = [
  "Weather",
  "News",
  "To-Do",
  "Stock",
  "Quiz",
  "Writing Feedback",
  "Joke",
];

function App() {
  const [agent, setAgent] = useState("Weather");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Add empty bot message that we'll update as tokens arrive
    const botMessageId = Date.now();
    const botMessage = {
      sender: "bot",
      text: "",
      id: botMessageId,
      isLoading: true,
    };
    setMessages((prev) => [...prev, botMessage]);

    const inputValue = input;
    setInput("");

    try {
      const response = await fetch("http://localhost:5000/api/agent", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          agent,
          message: inputValue,
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let firstToken = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) {
                // Remove loading state when first token arrives
                if (firstToken) {
                  setIsLoading(false);
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === botMessageId
                        ? { ...msg, isLoading: false }
                        : msg
                    )
                  );
                  firstToken = false;
                }

                // Update the bot message with new token
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === botMessageId
                      ? { ...msg, text: msg.text + data.token }
                      : msg
                  )
                );
              }
              if (data.done) {
                break;
              }
            } catch (e) {
              console.error("Error parsing SSE data:", e);
            }
          }
        }
      }
    } catch (err) {
      console.error("Error:", err);
      setIsLoading(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMessageId
            ? { ...msg, text: "Error contacting agent.", isLoading: false }
            : msg
        )
      );
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <div className="container">
      <div className="header">
        <div className="agent-dropdown">
          <select
            value={agent}
            onChange={(e) => {
              setAgent(e.target.value);
              setMessages([]);
            }}
            className="agent-selector"
          >
            {AGENTS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>
        <h1 className="title">Agents</h1>
        <div className="header-spacer"></div>
      </div>
      <div className="chat-window">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>How can I help you today? 😊</h2>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={msg.id || i}
            className={`message ${msg.sender === "user" ? "user" : "bot"}`}
          >
            <div className="message-content">
              {msg.sender === "user" ? (
                <div className="message-bubble">{msg.text}</div>
              ) : (
                <div style={{ whiteSpace: "pre-wrap" }}>
                  {msg.isLoading ? (
                    <div className="loading-message">
                      <div className="loading-spinner"></div>
                      Thinking...
                    </div>
                  ) : (
                    msg.text
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <div className="input-container">
        <div className="input-box">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask anything"
          />
          <button onClick={handleSend} disabled={!input.trim() || isLoading}>
            ↑
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
