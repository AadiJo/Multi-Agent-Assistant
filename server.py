import subprocess
import socket
import time
import json
import requests
from threading import Thread
from flask import Flask, request, Response
from flask_cors import CORS

# Import all agents
from agents import (
    WeatherAgent, NewsAgent, TodoAgent, StockAgent, 
    QuizAgent, WritingFeedbackAgent, JokeAgent
)

app = Flask(__name__)
CORS(app)

def is_port_open(host, port):
    """Check if a port is open on localhost"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def start_ollama_server():
    """Start Ollama server if not running"""
    if not is_port_open("localhost", 11434):
        print("Starting Ollama server...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for Ollama to be ready
        for _ in range(10):
            if is_port_open("localhost", 11434):
                print("Ollama server started.")
                return
            time.sleep(1)
        raise RuntimeError("Failed to start Ollama server.")
    else:
        print("Ollama server already running.")


# Initialize agents
agents_registry = {
    "Weather": WeatherAgent(),
    "News": NewsAgent(),
    "To-Do": TodoAgent(),
    "Stock": StockAgent(),
    "Quiz": QuizAgent(),
    "Writing Feedback": WritingFeedbackAgent(),
    "Joke": JokeAgent(),
}


@app.route("/api/models", methods=["GET"])
def get_models():
    """Get available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            models = [model["name"] for model in models_data.get("models", [])]
            return {"models": models}
        else:
            return {"models": ["mistral"]}, 500
    except Exception as e:
        print(f"Error fetching models: {e}")
        return {"models": ["mistral"]}, 500


@app.route("/api/agent", methods=["POST"])
def handle_agent():
    """Handle agent requests with streaming responses"""
    data = request.json
    agent_name = data.get("agent")
    message = data.get("message")
    model = data.get("model", "mistral")  # Default to mistral if no model specified

    agent = agents_registry.get(agent_name)
    if not agent:
        def error_generator():
            yield f"data: {json.dumps({'token': 'Unknown agent.', 'done': True})}\n\n"
        return Response(error_generator(), mimetype='text/plain')

    # Update agent model if different from current
    if hasattr(agent, 'model') and agent.model != model:
        agent.model = model

    def generate():
        """Generate streaming response"""
        full_response = ""
        try:
            for token in agent.stream_response(message):
                full_response += token
                yield f"data: {json.dumps({'token': token, 'done': False})}\n\n"
            yield f"data: {json.dumps({'token': '', 'done': True, 'full_response': full_response})}\n\n"
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'token': error_msg, 'done': True})}\n\n"

    return Response(generate(), mimetype='text/plain')


if __name__ == "__main__":
    print("Multi-Agent Assistant starting...")
    
    # Start Ollama server in background thread
    Thread(target=start_ollama_server, daemon=True).start()
    
    # Start Flask server
    print("Starting Flask server on port 5000...")
    app.run(port=5000, debug=True)
