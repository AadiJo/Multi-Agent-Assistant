#!/usr/bin/env python3
"""
Command-line runner for all agents
Usage: python run_agent.py [agent_name]
Available agents: basic, weather, news, todo, stock, quiz, writing, joke
"""

import sys
from agents import (
    WeatherAgent, NewsAgent, TodoAgent, StockAgent,
    QuizAgent, WritingFeedbackAgent, JokeAgent, BasicAgent
)

AGENTS = {
    'basic': BasicAgent,
    'weather': WeatherAgent,
    'news': NewsAgent,
    'todo': TodoAgent,
    'stock': StockAgent,
    'quiz': QuizAgent,
    'writing': WritingFeedbackAgent,
    'joke': JokeAgent,
}

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_agent.py [agent_name]")
        print(f"Available agents: {', '.join(AGENTS.keys())}")
        sys.exit(1)
    
    agent_name = sys.argv[1].lower()
    if agent_name not in AGENTS:
        print(f"Unknown agent: {agent_name}")
        print(f"Available agents: {', '.join(AGENTS.keys())}")
        sys.exit(1)
    
    agent_class = AGENTS[agent_name]
    agent = agent_class()
    agent.run_cli()

if __name__ == "__main__":
    main()
