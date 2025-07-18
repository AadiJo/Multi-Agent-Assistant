# Multi-Agent Assistant

A collection of AI agents built with Ollama for various tasks including weather, news, and productivity.

## Features

- **Basic Agent**: General conversation agent with no system prompt for natural chat
- **Weather Agent**: Provides detailed weather information with location detection
- **News Agent**: Summarizes current headlines and answers news-related questions
- **Todo Agent**: Manages tasks and to-do lists through natural language
- **Stock Agent**: Offers financial advice and stock market insights
- **Quiz Agent**: Generates quizzes and flashcards on any topic
- **Writing Feedback Agent**: Reviews writing for clarity, grammar, and coherence
- **Joke Agent**: Tells clean jokes and shares fun facts
- **Chat History**: Automatic storage and retrieval of all conversations with model tracking

## 📋 Prerequisites

- Python 3.7+
- [Ollama](https://ollama.com) installed and accessible from command line
- Internet connection for weather/news data

## 🛠️ Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd <folder-name>
```

2. Install Python dependencies:

```bash
pip install requests flask flask-cors
```

3. Install and start Ollama:

```bash
# Install Ollama from https://ollama.com
# The agents will automatically pull the required model (mistral) on first run
```

## Usage

### Web Interface

Start the web server:

```bash
python server.py
```

Then open the React frontend:

```bash
npm install
npm start
```

Navigate to `http://localhost:3000` to use the web interface.

### Command Line Interface

Each agent can be run individually in the terminal with live streaming responses:

#### Run specific agents:

```bash
# Basic agent
python -m agents.basic_agent

# Weather agent
python -m agents.weather_agent

# News agent
python -m agents.news_agent

# Todo agent
python -m agents.todo_agent

# Stock agent
python -m agents.stock_agent

# Quiz agent
python -m agents.quiz_agent

# Writing feedback agent
python -m agents.writing_feedback_agent

# Joke agent
python -m agents.joke_agent
```

#### Or use the unified runner:

```bash
python run_agent.py basic
python run_agent.py weather
python run_agent.py news
python run_agent.py todo
python run_agent.py stock
python run_agent.py quiz
python run_agent.py writing
python run_agent.py joke
```

### CLI Features

- **Live Streaming**: Responses stream in real-time as they're generated
- **Colored Output**: Action items and conclusions highlighted in red
- **Custom Loading Messages**: Context-aware loading messages for each agent
- **Auto-Setup**: Automatically starts Ollama and downloads required models
- **Chat History**: All conversations automatically saved with session IDs

## File Structure

```
├── server.py                       # Flask web server
├── run_agent.py                    # CLI runner utility
├── chat_storage.py                 # Chat history storage system
├── chat_manager.py                 # Command-line chat history manager
├── agents/                         # Agent implementations
│   ├── __init__.py                 # Package exports
│   ├── base.py                     # Base classes with streaming support
│   ├── basic_agent.py              # Basic conversational agent
│   ├── weather_agent.py            # Weather information agent
│   ├── news_agent.py               # News analysis agent
│   ├── todo_agent.py               # Task management agent
│   ├── stock_agent.py              # Financial advice agent
│   ├── quiz_agent.py               # Educational quiz agent
│   ├── writing_feedback_agent.py   # Writing analysis agent
│   └── joke_agent.py               # Entertainment agent
├── chat_history/                   # Stored chat sessions (auto-created)
└── src/                            # React frontend
    ├── App.js                      # Main React component
    ├── App.css                     # Application styles
    └── index.js                    # React entry point
```

## Chat History Management

All conversations are automatically stored with:
- Session IDs for easy retrieval
- Agent and model information
- Complete message history with timestamps
- Search and export capabilities

### Web Interface Chat History

- **📚 History Button**: View all previous chat sessions
- **➕ New Chat**: Start a fresh conversation
- **Session Management**: Load previous conversations or delete old ones
- **Visual Timeline**: See when conversations occurred and with which agents

### Command Line Chat History

```bash
# List all chat sessions
python chat_manager.py list

# View a specific session
python chat_manager.py view <session_id>

# Search for sessions containing specific text
python chat_manager.py search "your search query"

# Delete a session
python chat_manager.py delete <session_id>

# Export a session
python chat_manager.py export <session_id> --format json
python chat_manager.py export <session_id> --format txt
```

## Next Steps

- Chat history
- Agent Creator
