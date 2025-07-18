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
    QuizAgent, WritingFeedbackAgent, JokeAgent, BasicAgent
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
    "Basic": BasicAgent(),
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
        """Generate streaming response with loading status updates"""
        full_response = ""
        try:
            # Custom generator that yields loading messages and tokens
            def agent_stream_with_status():
                # Initial loading message
                loading_message = getattr(agent, '_loading_message', 'Thinking...')
                yield {'status': 'loading', 'message': loading_message}
                
                # Get system prompt (usually quick)
                system_prompt = agent.get_system_prompt()
                
                # Check if loading message changed
                current_loading_message = getattr(agent, '_loading_message', 'Thinking...')
                if current_loading_message != loading_message:
                    yield {'status': 'loading', 'message': current_loading_message}
                    loading_message = current_loading_message
                
                # Prepare prompt (this is where agents do their background work)
                prompt = agent.prepare_prompt(message)
                
                # Check if loading message changed again
                current_loading_message = getattr(agent, '_loading_message', 'Thinking...')
                if current_loading_message != loading_message:
                    yield {'status': 'loading', 'message': current_loading_message}
                    loading_message = current_loading_message
                
                # Now stream the actual response
                payload = {
                    "model": agent.model,
                    "system": system_prompt,
                    "prompt": prompt,
                    "stream": True
                }
                
                response = requests.post("http://localhost:11434/api/generate", json=payload, stream=True)
                first_token = True
                
                for line in response.iter_lines():
                    if line:
                        try:
                            json_response = json.loads(line.decode('utf-8'))
                            if 'response' in json_response:
                                token = json_response['response']
                                if first_token:
                                    token = token.lstrip()
                                    first_token = False
                                yield {'token': token, 'done': False}
                            if json_response.get('done', False):
                                yield {'token': '', 'done': True}
                                break
                        except json.JSONDecodeError:
                            continue
            
            # Process the generator and send appropriate responses
            for item in agent_stream_with_status():
                if 'status' in item:
                    # This is a loading message
                    yield f"data: {json.dumps(item)}\n\n"
                elif 'token' in item:
                    # This is a token from the AI
                    full_response += item['token']
                    if item.get('done', False):
                        item['full_response'] = full_response
                    yield f"data: {json.dumps(item)}\n\n"
                    
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
