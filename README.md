# Multi-Agent Assistant

A collection of AI agents built with Ollama for various tasks including weather, news, and productivity.

## Features

- **Weather Agent**: Provides detailed weather information with location detection
- **News Agent**: Summarizes current headlines and answers news-related questions
- **Todo Agent**: Manages tasks and to-do lists through natural language
- **Stock Agent**: Offers financial advice and stock market insights
- **Quiz Agent**: Generates quizzes and flashcards on any topic
- **Writing Feedback Agent**: Reviews writing for clarity, grammar, and coherence
- **Joke Agent**: Tells clean jokes and shares fun facts

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
- **Auto-Setup**: Automatically starts Ollama and downloads required models

## File Structure
```
├── main.py                         # Web server (Flask)
├── run_agent.py                    # CLI runner utility
├── agents/                         # Agent implementations
│   ├── __init__.py                 # Package exports  
│   └── base.py                     # Base classes with streaming support
└── app/                            # React frontend
    ├── src/
    ├── public/
    └── package.json
```

## Next Steps
- Chat history