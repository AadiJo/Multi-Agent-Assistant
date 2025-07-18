import json
import requests
import subprocess
import socket
import sys
import time
import threading
from abc import ABC, abstractmethod
from typing import Optional

# Import chat storage
try:
    from ..chat_storage import chat_storage
except ImportError:
    try:
        from chat_storage import chat_storage
    except ImportError:
        # Fallback if chat_storage is not available
        chat_storage = None

OLLAMA_MODEL = "mistral"
OLLAMA_URL = "http://localhost:11434/api/generate"

# Color codes for terminal output
class Colors:
    LIGHT_BLUE = '\033[94m'
    RED = '\033[91m'
    RESET = '\033[0m'


class LoadingAnimation:
    """NPM-style rectangle loading animation for CLI"""
    
    def __init__(self, message="Thinking..."):
        self.animation_chars = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
        self.running = False
        self.thread = None
        self.message = message
    
    def start(self):
        """Start the loading animation"""
        self.running = True
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the loading animation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.2)  # Add timeout to avoid hanging
        # Clear the loading line completely and ensure cursor is at start of line
        print('\r' + ' ' * 80 + '\r', end='', flush=True)
    
    def update_message(self, message):
        """Update the loading message"""
        self.message = message
    
    def _animate(self):
        """Run the animation loop"""
        i = 0
        while self.running:
            char = self.animation_chars[i % len(self.animation_chars)]
            print(f'\r{Colors.LIGHT_BLUE}{char} {self.message}{Colors.RESET}', end='', flush=True)
            time.sleep(0.1)
            i += 1


def ensure_ollama_running():
    """Ensure Ollama server is running"""
    def is_port_open(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    def is_ollama_installed():
        try:
            result = subprocess.run(
                ["ollama", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    if not is_ollama_installed():
        print("Ollama is not installed or not accessible. Please install it from https://ollama.com")
        print("Make sure Ollama is added to your system PATH.")
        sys.exit(1)

    if not is_port_open("localhost", 11434):
        print("Starting Ollama server...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
        if not is_port_open("localhost", 11434):
            print("Failed to start Ollama. Is it installed correctly?")
            sys.exit(1)


def ensure_model_downloaded(model=OLLAMA_MODEL):
    """Ensure the specified model is downloaded"""
    print(f"Checking if model '{model}' is available...")
    models = requests.get("http://localhost:11434/api/tags").json()
    if not any(model in m["name"] for m in models.get("models", [])):
        print(f"Pulling model '{model}'...")
        subprocess.run(["ollama", "pull", model], check=True)


class BaseAgent(ABC):
    """Base class for all agents with streaming support"""
    
    def __init__(self, model=OLLAMA_MODEL):
        self.model = model
        self._loading_message = 'Thinking...'
        self._current_session_id = None
    
    def set_loading_message(self, message):
        """Set custom loading message for background tasks"""
        self._loading_message = message
    
    def set_session_id(self, session_id: str):
        """Set the current chat session ID"""
        self._current_session_id = session_id
    
    def get_session_id(self) -> Optional[str]:
        """Get the current chat session ID"""
        return self._current_session_id
    
    @abstractmethod
    def get_system_prompt(self):
        """Return the system prompt for this agent"""
        pass
    
    @abstractmethod
    def prepare_prompt(self, user_message):
        """Prepare the prompt for this agent given a user message"""
        pass
    
    def stream_response(self, user_message):
        """Stream the response from Ollama"""
        # Set default loading message
        self.set_loading_message("Thinking...")
        
        system_prompt = self.get_system_prompt()
        prompt = self.prepare_prompt(user_message)
        
        # Set final loading message for AI generation
        self.set_loading_message("Generating response...")
        
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": True
        }
        
        try:
            response = requests.post(OLLAMA_URL, json=payload, stream=True)
            first_token = True
            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line.decode('utf-8'))
                        if 'response' in json_response:
                            token = json_response['response']
                            # Strip leading whitespace from the first token only
                            if first_token:
                                token = token.lstrip()
                                first_token = False
                            yield token
                        if json_response.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def stream_response_with_colors(self, user_message):
        """Stream response with colored output for terminal use"""
        # Get custom loading message if available
        loading_message = getattr(self, '_loading_message', 'Thinking...')
        
        # Start loading animation
        loader = LoadingAnimation(loading_message)
        loader.start()
        
        full_response = ""
        first_token = True
        
        try:
            # Get system prompt first (this shouldn't print anything)
            system_prompt = self.get_system_prompt()
            
            # Stop loading animation before prepare_prompt (which might print things)
            loader.stop()
            
            # Prepare prompt (this might print status messages)
            prompt = self.prepare_prompt(user_message)
            
            # Get updated loading message in case it changed during prepare_prompt
            loading_message = getattr(self, '_loading_message', 'Thinking...')
            
            # Restart loading animation for the actual LLM call
            loader = LoadingAnimation(loading_message)
            loader.start()
            
            # Now make the streaming request
            payload = {
                "model": self.model,
                "system": system_prompt,
                "prompt": prompt,
                "stream": True
            }
            
            response = requests.post(OLLAMA_URL, json=payload, stream=True)
            
            for line in response.iter_lines():
                if line:
                    try:
                        json_response = json.loads(line.decode('utf-8'))
                        if 'response' in json_response:
                            token = json_response['response']
                            
                            # Stop loading animation when first token arrives
                            if first_token:
                                loader.stop()
                                # Strip leading whitespace from the first token only
                                token = token.lstrip()
                                first_token = False
                            
                            full_response += token
                            # Print token with appropriate color for ACTION items
                            if token.strip().startswith('ACTION:') or 'ACTION:' in full_response.split('\n')[-1]:
                                print(f"{Colors.RED}{token}{Colors.RESET}", end='', flush=True)
                            else:
                                print(f"{Colors.LIGHT_BLUE}{token}{Colors.RESET}", end='', flush=True)
                        
                        if json_response.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            full_response = f"Error: {str(e)}"
            print(f"{Colors.RED}{full_response}{Colors.RESET}", end='', flush=True)
        
        finally:
            # Always ensure loader is stopped, even if an exception occurs
            loader.stop()
        
        return full_response
    
    @abstractmethod
    def get_agent_name(self):
        """Return the display name of this agent"""
        pass
    
    @abstractmethod 
    def get_prompt_text(self):
        """Return the prompt text for user input"""
        pass
    
    def run_cli(self):
        """Run the agent in command-line interface mode"""
        print(f"AI {self.get_agent_name()} is starting...")
        
        ensure_ollama_running()
        ensure_model_downloaded()
        
        # Agent-specific initialization
        if hasattr(self, 'initialize'):
            if not self.initialize():
                return
        
        # Create a new chat session
        session_id = None
        if chat_storage:
            session_id = chat_storage.create_chat_session(self.get_agent_name(), self.model)
            self.set_session_id(session_id)
            print(f"Chat session created: {session_id}")
        
        print(f"\n{self.get_agent_name()} is ready!")
        if session_id:
            print(f"Chat history will be saved to: chat_history/{session_id}.json")
        print()
        
        while True:
            q = input(f"{self.get_prompt_text()} (or type 'exit'): ").strip()
            if q.lower() in ("exit", "quit"):
                break
            
            # Store user message
            if chat_storage and session_id:
                chat_storage.add_message(session_id, "user", q)
            
            print()  # Add a newline before the response
            response = self.stream_response_with_colors(q)
            
            # Store bot response
            if chat_storage and session_id:
                chat_storage.add_message(session_id, "bot", response)
            
            print("\n")  # Add newlines after the response


class SimpleAgent(BaseAgent):
    """Simple agent that takes a system prompt and uses it directly"""
    
    def __init__(self, system_prompt, agent_name="Assistant", prompt_text="Ask a question", model=OLLAMA_MODEL):
        super().__init__(model)
        self._system_prompt = system_prompt
        self._agent_name = agent_name
        self._prompt_text = prompt_text
    
    def get_system_prompt(self):
        return self._system_prompt
    
    def prepare_prompt(self, user_message):
        return user_message
    
    def get_agent_name(self):
        return self._agent_name
    
    def get_prompt_text(self):
        return self._prompt_text
