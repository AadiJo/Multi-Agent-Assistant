#!/usr/bin/env python3
"""
Chat History Manager
Utility to view, search, and manage chat history
"""

import argparse
import json
from datetime import datetime
from chat_storage import chat_storage


def list_sessions(agent_filter=None):
    """List all chat sessions"""
    sessions = chat_storage.list_chat_sessions(agent_filter)
    
    if not sessions:
        print("No chat sessions found.")
        return
    
    print(f"Found {len(sessions)} chat session(s):")
    print("-" * 80)
    
    for session in sessions:
        print(f"Session ID: {session['session_id']}")
        print(f"Agent: {session['agent_name']}")
        print(f"Model: {session['model']}")
        print(f"Messages: {session['message_count']}")
        print(f"Created: {session['created_at']}")
        print(f"Updated: {session['updated_at']}")
        if session['first_message']:
            print(f"First message: {session['first_message'][:100]}...")
        print("-" * 80)


def view_session(session_id):
    """View a specific chat session"""
    chat_data = chat_storage.load_chat_session(session_id)
    
    if not chat_data:
        print(f"Session {session_id} not found.")
        return
    
    print(f"Chat Session: {session_id}")
    print(f"Agent: {chat_data['agent_name']}")
    print(f"Model: {chat_data['model']}")
    print(f"Created: {chat_data['created_at']}")
    print(f"Updated: {chat_data['updated_at']}")
    print("=" * 80)
    
    for i, message in enumerate(chat_data['messages'], 1):
        timestamp = datetime.fromisoformat(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        sender = message['sender'].upper()
        content = message['message']
        
        print(f"\n[{i}] {timestamp} - {sender}:")
        print(content)
        print("-" * 40)


def search_sessions(query, agent_filter=None):
    """Search for sessions containing specific text"""
    results = chat_storage.search_chats(query, agent_filter)
    
    if not results:
        print(f"No sessions found containing '{query}'.")
        return
    
    print(f"Found {len(results)} session(s) containing '{query}':")
    print("-" * 80)
    
    for result in results:
        print(f"Session ID: {result['session_id']}")
        print(f"Agent: {result['agent_name']}")
        print(f"Model: {result['model']}")
        print(f"Messages: {result['message_count']}")
        print(f"Matching content: {result['matching_message'][:150]}...")
        print("-" * 80)


def delete_session(session_id):
    """Delete a chat session"""
    if chat_storage.delete_chat_session(session_id):
        print(f"Session {session_id} deleted successfully.")
    else:
        print(f"Session {session_id} not found.")


def export_session(session_id, format_type='json'):
    """Export a chat session"""
    exported_data = chat_storage.export_chat_session(session_id, format_type)
    
    if exported_data:
        filename = f"chat_{session_id}.{format_type}"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(exported_data)
        print(f"Session exported to {filename}")
    else:
        print(f"Session {session_id} not found.")


def main():
    parser = argparse.ArgumentParser(description='Chat History Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List sessions
    list_parser = subparsers.add_parser('list', help='List all chat sessions')
    list_parser.add_argument('--agent', help='Filter by agent name')
    
    # View session
    view_parser = subparsers.add_parser('view', help='View a specific chat session')
    view_parser.add_argument('session_id', help='Session ID to view')
    
    # Search sessions
    search_parser = subparsers.add_parser('search', help='Search for sessions')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--agent', help='Filter by agent name')
    
    # Delete session
    delete_parser = subparsers.add_parser('delete', help='Delete a chat session')
    delete_parser.add_argument('session_id', help='Session ID to delete')
    
    # Export session
    export_parser = subparsers.add_parser('export', help='Export a chat session')
    export_parser.add_argument('session_id', help='Session ID to export')
    export_parser.add_argument('--format', choices=['json', 'txt'], default='json', help='Export format')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_sessions(args.agent)
    elif args.command == 'view':
        view_session(args.session_id)
    elif args.command == 'search':
        search_sessions(args.query, args.agent)
    elif args.command == 'delete':
        delete_session(args.session_id)
    elif args.command == 'export':
        export_session(args.session_id, args.format)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
