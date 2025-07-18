import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const AGENTS = [
  "Basic",
  "Weather",
  "News",
  "To-Do",
  "Stock",
  "Quiz",
  "Writing Feedback",
  "Joke",
];

// Function to process text and style <think> tags
const processTextWithThinkTags = (text) => {
  if (!text || typeof text !== "string") return text;

  // Split text by <think> and </think> tags
  const parts = text.split(/(<think>|<\/think>)/);
  const result = [];
  let isInThinkTag = false;
  let key = 0;

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];

    if (part === "<think>") {
      isInThinkTag = true;
    } else if (part === "</think>") {
      isInThinkTag = false;
    } else if (part) {
      if (isInThinkTag) {
        result.push(
          <span key={key++} className="think-content">
            {part}
          </span>
        );
      } else {
        result.push(part);
      }
    }
  }

  return result.length === 1 && typeof result[0] === "string"
    ? result[0]
    : result;
};

function App() {
  const [agent, setAgent] = useState("Basic");
  const [model, setModel] = useState("mistral");
  const [availableModels, setAvailableModels] = useState(["mistral"]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [abortController, setAbortController] = useState(null);
  const [shouldStop, setShouldStop] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [chatSessions, setChatSessions] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    // Fetch available models on component mount
    const fetchModels = async () => {
      try {
        const response = await fetch("http://localhost:5000/api/models");
        const data = await response.json();
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models);
          // Set first model as default if mistral is not available
          if (!data.models.includes("mistral") && data.models.length > 0) {
            setModel(data.models[0]);
          }
        }
      } catch (error) {
        console.error("Error fetching models:", error);
        // Keep default mistral model if fetch fails
      }
    };
    fetchModels();
    loadChatSessions();
  }, []);

  const loadChatSessions = async () => {
    try {
      const response = await fetch("http://localhost:5000/api/chat/sessions");
      const data = await response.json();
      setChatSessions(data.sessions || []);
    } catch (error) {
      console.error("Error loading chat sessions:", error);
    }
  };

  const loadChatSession = async (sessionId) => {
    try {
      const response = await fetch(`http://localhost:5000/api/chat/session/${sessionId}`);
      const data = await response.json();
      
      if (data.messages) {
        const formattedMessages = data.messages.map((msg, index) => ({
          id: index,
          sender: msg.sender,
          text: msg.message,
          timestamp: msg.timestamp
        }));
        setMessages(formattedMessages);
        setCurrentSessionId(sessionId);
        setAgent(data.agent_name || "Basic");
        setModel(data.model || "mistral");
        setShowHistory(false);
      }
    } catch (error) {
      console.error("Error loading chat session:", error);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    setShowHistory(false);
  };

  const deleteChatSession = async (sessionId) => {
    try {
      const response = await fetch(`http://localhost:5000/api/chat/session/${sessionId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        loadChatSessions();
        if (currentSessionId === sessionId) {
          startNewChat();
        }
      }
    } catch (error) {
      console.error("Error deleting chat session:", error);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setIsStreaming(false);
    setShouldStop(false);

    // Create abort controller for this request
    const controller = new AbortController();
    setAbortController(controller);

    // Add empty bot message that we'll update as tokens arrive
    const botMessageId = Date.now();
    const botMessage = {
      sender: "bot",
      text: "",
      id: botMessageId,
      isLoading: true,
      loadingMessage: "Thinking...", // Default loading message
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
          model,
          session_id: currentSessionId,
        }),
        signal: controller.signal, // Add abort signal
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let firstToken = true;

      while (true) {
        // Check if we should stop processing
        if (shouldStop || controller.signal.aborted) {
          reader.cancel();
          break;
        }

        const { done, value } = await reader.read();
        if (done) break;

        // Check again after read
        if (shouldStop || controller.signal.aborted) {
          reader.cancel();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          // Check for stop before processing each line
          if (shouldStop || controller.signal.aborted) {
            reader.cancel();
            return;
          }

          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              
              // Handle status updates (loading messages)
              if (data.status === 'loading') {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === botMessageId
                      ? { ...msg, loadingMessage: data.message }
                      : msg
                  )
                );
              }
              
              if (data.token) {
                // Remove loading state when first token arrives, but start streaming
                if (firstToken) {
                  setIsLoading(false);
                  setIsStreaming(true);
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === botMessageId
                        ? { ...msg, isLoading: false }
                        : msg
                    )
                  );
                  firstToken = false;
                }

                // Check for stop after updating message
                if (shouldStop || controller.signal.aborted) {
                  reader.cancel();
                  return;
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
                setIsStreaming(false);
                // Update session ID if this was a new chat
                if (data.session_id && !currentSessionId) {
                  setCurrentSessionId(data.session_id);
                  loadChatSessions(); // Refresh the sessions list
                }
                break;
              }
            } catch (e) {
              console.error("Error parsing SSE data:", e);
            }
          }
        }
      }
    } catch (err) {
      if (err.name === "AbortError") {
        // Request was aborted - just remove loading state, don't add stop message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMessageId ? { ...msg, isLoading: false, loadingMessage: "" } : msg
          )
        );
      } else {
        console.error("Error:", err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMessageId
              ? { ...msg, text: "Error contacting agent.", isLoading: false, loadingMessage: "" }
              : msg
          )
        );
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      setAbortController(null);
      setShouldStop(false);
    }
  };

  const handleStop = () => {
    if (abortController) {
      setShouldStop(true);
      abortController.abort();
      setIsLoading(false);
      setIsStreaming(false);
      setAbortController(null);

      // Just remove the loading state without adding stop message
      setMessages((prev) =>
        prev.map((msg) => (msg.isLoading ? { ...msg, isLoading: false, loadingMessage: "" } : msg))
      );
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !isLoading && !isStreaming) {
      handleSend();
    } else if (e.key === "Escape" && (isLoading || isStreaming)) {
      handleStop();
    }
  };

  return (
    <div className="container">
      <div className="header">
        <div className="left-controls">
          <button 
            onClick={() => setShowHistory(!showHistory)}
            className="history-button"
            title="View Chats"
          >
            <div className="hamburger-icon">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </button>
          <button 
            onClick={startNewChat}
            className="new-chat-button"
            title="Add Chat"
          >
            <div className="plus-icon">
              <span className="horizontal"></span>
              <span className="vertical"></span>
            </div>
          </button>
        </div>
        <div className="agent-dropdown">
          <select
            value={agent}
            onChange={(e) => {
              setAgent(e.target.value);
              if (!currentSessionId) {
                setMessages([]);
              }
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
        <h1 className="title">Multi-Agent Assistant</h1>
        <div className="model-dropdown">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="model-selector"
            title="Select Ollama Model"
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {showHistory && (
        <div className="chat-history-panel">
          <div className="history-header">
            <h3>Chat History</h3>
            <button onClick={() => setShowHistory(false)} className="close-button">×</button>
          </div>
          <div className="history-list">
            {chatSessions.map((session) => (
              <div key={session.session_id} className="history-item">
                <div className="history-item-content" onClick={() => loadChatSession(session.session_id)}>
                  <div className="history-item-header">
                    <span className="agent-name">{session.agent_name}</span>
                    <span className="model-name">{session.model}</span>
                  </div>
                  <div className="history-item-preview">
                    {session.first_message}
                  </div>
                  <div className="history-item-meta">
                    <span className="message-count">{session.message_count} messages</span>
                    <span className="timestamp">{new Date(session.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteChatSession(session.session_id);
                  }}
                  className="delete-session-button"
                  title="Delete Session"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div className="chat-window">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>How can I help you today? 😊</h2>
            {currentSessionId && (
              <p className="session-info">Session: {currentSessionId}</p>
            )}
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
                      {msg.loadingMessage || "Thinking..."}
                    </div>
                  ) : (
                    processTextWithThinkTags(msg.text)
                  )}
                </div>
              )}
            </div>
            {msg.timestamp && (
              <div className="message-timestamp">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </div>
            )}
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
            placeholder={
              isLoading || isStreaming
                ? "Press Escape to stop..."
                : "Ask anything"
            }
            disabled={isLoading || isStreaming}
          />
          <button
            onClick={isLoading || isStreaming ? handleStop : handleSend}
            disabled={!input.trim() && !isLoading && !isStreaming}
            className={isLoading || isStreaming ? "stop-button" : "send-button"}
          >
            {isLoading || isStreaming ? "⏹" : "↑"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
