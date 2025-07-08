import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const AGENTS = [
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
  const [agent, setAgent] = useState("Weather");
  const [model, setModel] = useState("mistral");
  const [availableModels, setAvailableModels] = useState(["mistral"]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [abortController, setAbortController] = useState(null);
  const [shouldStop, setShouldStop] = useState(false);
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
  }, []);

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
            msg.id === botMessageId ? { ...msg, isLoading: false } : msg
          )
        );
      } else {
        console.error("Error:", err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMessageId
              ? { ...msg, text: "Error contacting agent.", isLoading: false }
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
        prev.map((msg) => (msg.isLoading ? { ...msg, isLoading: false } : msg))
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
                    processTextWithThinkTags(msg.text)
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
