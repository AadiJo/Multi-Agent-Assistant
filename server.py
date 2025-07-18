import subprocess
import socket
import time
import json
import requests
from threading import Thread
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from chat_storage import chat_storage

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
    session_id = data.get("session_id")  # Optional session ID

    agent = agents_registry.get(agent_name)
    if not agent:
        def error_generator():
            yield f"data: {json.dumps({'token': 'Unknown agent.', 'done': True})}\n\n"
        return Response(error_generator(), mimetype='text/plain')

    # Update agent model if different from current
    if hasattr(agent, 'model') and agent.model != model:
        agent.model = model

    # Create new session if not provided
    if not session_id:
        session_id = chat_storage.create_chat_session(agent_name, model)
    
    # Set session ID for the agent
    agent.set_session_id(session_id)
    
    # Store user message
    chat_storage.add_message(session_id, "user", message)

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
                        item['session_id'] = session_id
                        # Store bot response when done
                        chat_storage.add_message(session_id, "bot", full_response)
                    yield f"data: {json.dumps(item)}\n\n"
                    
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'token': error_msg, 'done': True})}\n\n"

    return Response(generate(), mimetype='text/plain')


@app.route("/api/chat/sessions", methods=["GET"])
def get_chat_sessions():
    """Get list of all chat sessions"""
    agent_name = request.args.get('agent')
    sessions = chat_storage.list_chat_sessions(agent_name)
    return jsonify({"sessions": sessions})


@app.route("/api/chat/session/<session_id>", methods=["GET"])
def get_chat_session(session_id):
    """Get a specific chat session"""
    chat_data = chat_storage.load_chat_session(session_id)
    if chat_data:
        return jsonify(chat_data)
    else:
        return jsonify({"error": "Session not found"}), 404


@app.route("/api/chat/session/<session_id>", methods=["DELETE"])
def delete_chat_session(session_id):
    """Delete a specific chat session"""
    success = chat_storage.delete_chat_session(session_id)
    if success:
        return jsonify({"message": "Session deleted successfully"})
    else:
        return jsonify({"error": "Session not found"}), 404


@app.route("/api/chat/session/<session_id>/history", methods=["GET"])
def get_chat_history(session_id):
    """Get chat history for a specific session"""
    history = chat_storage.get_chat_history(session_id)
    return jsonify({"history": history})


@app.route("/api/chat/search", methods=["GET"])
def search_chats():
    """Search for chats containing specific text"""
    query = request.args.get('q', '')
    agent_name = request.args.get('agent')
    
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    results = chat_storage.search_chats(query, agent_name)
    return jsonify({"results": results})


@app.route("/api/chat/session/<session_id>/export", methods=["GET"])
def export_chat_session(session_id):
    """Export a chat session"""
    format_type = request.args.get('format', 'json')
    exported_data = chat_storage.export_chat_session(session_id, format_type)
    
    if exported_data:
        if format_type.lower() == 'json':
            return Response(exported_data, mimetype='application/json')
        elif format_type.lower() == 'txt':
            return Response(exported_data, mimetype='text/plain')
        else:
            return jsonify({"error": "Unsupported format"}), 400
    else:
        return jsonify({"error": "Session not found"}), 404


if __name__ == "__main__":
    print("Multi-Agent Assistant starting...")
    
    # Start Ollama server in background thread
    Thread(target=start_ollama_server, daemon=True).start()
    
    # Start Flask server
    print("Starting Flask server on port 5000...")
    app.run(port=5000, debug=True)
