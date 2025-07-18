# Handle both relative and absolute imports
try:
    from .base import BaseAgent
except ImportError:
    from base import BaseAgent


class BasicAgent(BaseAgent):
    """Basic conversational agent with no system prompt for general chat"""
    
    def get_system_prompt(self):
        """Return an empty system prompt for natural conversation"""
        return ""
    
    def prepare_prompt(self, user_message):
        """Set custom loading message for basic conversation"""
        self.set_loading_message("Thinking...")
        return user_message
    
    def get_agent_name(self):
        return "Basic Agent"
    
    def get_prompt_text(self):
        return "Ask me anything"


def main():
    """CLI entry point for basic agent"""
    agent = BasicAgent()
    agent.run_cli()


if __name__ == "__main__":
    main()
