import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import uuid


class ChatStorage:
    """Handles storing and retrieving chat conversations"""
    
    def __init__(self, storage_dir: str = "chat_history"):
        self.storage_dir = storage_dir
        self.ensure_storage_dir()
        
    def ensure_storage_dir(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def create_chat_session(self, agent_name: str, model: str) -> str:
        """Create a new chat session and return session ID"""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        chat_data = {
            "session_id": session_id,
            "agent_name": agent_name,
            "model": model,
            "created_at": timestamp,
            "updated_at": timestamp,
            "messages": []
        }
        
        self.save_chat_session(chat_data)
        return session_id
    
    def add_message(self, session_id: str, sender: str, message: str, timestamp: Optional[str] = None):
        """Add a message to an existing chat session"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
            
        chat_data = self.load_chat_session(session_id)
        if chat_data:
            chat_data["messages"].append({
                "sender": sender,
                "message": message,
                "timestamp": timestamp
            })
            chat_data["updated_at"] = timestamp
            self.save_chat_session(chat_data)
            return True
        return False
    
    def load_chat_session(self, session_id: str) -> Optional[Dict]:
        """Load a chat session by ID"""
        filepath = os.path.join(self.storage_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def save_chat_session(self, chat_data: Dict):
        """Save chat session to file"""
        session_id = chat_data["session_id"]
        filepath = os.path.join(self.storage_dir, f"{session_id}.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving chat session: {e}")
    
    def list_chat_sessions(self, agent_name: Optional[str] = None) -> List[Dict]:
        """List all chat sessions, optionally filtered by agent"""
        sessions = []
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                session_id = filename[:-5]  # Remove .json extension
                chat_data = self.load_chat_session(session_id)
                
                if chat_data:
                    if agent_name is None or chat_data.get("agent_name") == agent_name:
                        # Add summary info
                        summary = {
                            "session_id": session_id,
                            "agent_name": chat_data.get("agent_name"),
                            "model": chat_data.get("model"),
                            "created_at": chat_data.get("created_at"),
                            "updated_at": chat_data.get("updated_at"),
                            "message_count": len(chat_data.get("messages", [])),
                            "first_message": chat_data.get("messages", [{}])[0].get("message", "")[:100] if chat_data.get("messages") else ""
                        }
                        sessions.append(summary)
        
        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions
    
    def delete_chat_session(self, session_id: str) -> bool:
        """Delete a chat session"""
        filepath = os.path.join(self.storage_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except OSError:
                return False
        return False
    
    def get_chat_history(self, session_id: str) -> List[Dict]:
        """Get all messages from a chat session"""
        chat_data = self.load_chat_session(session_id)
        if chat_data:
            return chat_data.get("messages", [])
        return []
    
    def search_chats(self, query: str, agent_name: Optional[str] = None) -> List[Dict]:
        """Search for chats containing specific text"""
        results = []
        query_lower = query.lower()
        
        for filename in os.listdir(self.storage_dir):
            if filename.endswith('.json'):
                session_id = filename[:-5]
                chat_data = self.load_chat_session(session_id)
                
                if chat_data:
                    if agent_name is None or chat_data.get("agent_name") == agent_name:
                        # Search in messages
                        for message in chat_data.get("messages", []):
                            if query_lower in message.get("message", "").lower():
                                summary = {
                                    "session_id": session_id,
                                    "agent_name": chat_data.get("agent_name"),
                                    "model": chat_data.get("model"),
                                    "created_at": chat_data.get("created_at"),
                                    "updated_at": chat_data.get("updated_at"),
                                    "message_count": len(chat_data.get("messages", [])),
                                    "matching_message": message.get("message", "")[:200]
                                }
                                results.append(summary)
                                break  # Only add each session once
        
        return results
    
    def export_chat_session(self, session_id: str, format: str = "json") -> Optional[str]:
        """Export a chat session to different formats"""
        chat_data = self.load_chat_session(session_id)
        if not chat_data:
            return None
        
        if format.lower() == "json":
            return json.dumps(chat_data, indent=2, ensure_ascii=False)
        
        elif format.lower() == "txt":
            lines = []
            lines.append(f"Chat Session: {session_id}")
            lines.append(f"Agent: {chat_data.get('agent_name')}")
            lines.append(f"Model: {chat_data.get('model')}")
            lines.append(f"Created: {chat_data.get('created_at')}")
            lines.append("-" * 50)
            
            for message in chat_data.get("messages", []):
                timestamp = message.get("timestamp", "")
                sender = message.get("sender", "")
                content = message.get("message", "")
                lines.append(f"\n[{timestamp}] {sender.upper()}:")
                lines.append(content)
            
            return "\n".join(lines)
        
        return None


# Global chat storage instance
chat_storage = ChatStorage()
