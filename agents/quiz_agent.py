# Handle both relative and absolute imports
try:
    from .base import BaseAgent
except ImportError:
    from base import BaseAgent

import requests
import json
from urllib.parse import quote


def search_web(query, num_results=3):
    """Search the web for information using DuckDuckGo Instant Answer API"""
    try:
        # Use DuckDuckGo Instant Answer API (free, no API key required)
        url = f"https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_redirect': '1',
            'no_html': '1',
            'skip_disambig': '1'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        results = []
        
        # Get abstract/summary if available
        if data.get('Abstract'):
            results.append({
                'title': data.get('AbstractSource', 'Summary'),
                'content': data.get('Abstract'),
                'url': data.get('AbstractURL', '')
            })
        
        # Get related topics
        for topic in data.get('RelatedTopics', [])[:num_results-1]:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append({
                    'title': topic.get('FirstURL', '').split('/')[-1] if topic.get('FirstURL') else 'Related Topic',
                    'content': topic.get('Text'),
                    'url': topic.get('FirstURL', '')
                })
        
        # If no good results, try a simple search approach
        if not results:
            # Fallback: Return a message indicating web search was attempted
            results.append({
                'title': 'Web Search Attempted',
                'content': f'Searched for: {query}. Consider using your existing knowledge to create relevant quiz questions.',
                'url': ''
            })
        
        return results[:num_results]
    
    except Exception as e:
        print(f"Web search error: {e}")
        return [{
            'title': 'Search Error',
            'content': f'Unable to fetch web information for: {query}. Using existing knowledge instead.',
            'url': ''
        }]


class QuizAgent(BaseAgent):
    """Advanced educational quiz and flashcard generation agent with web access"""
    
    
    def __init__(self):
        super().__init__()
        self._system_prompt = """
You are an expert educator and learning specialist who creates engaging, educational quizzes and flashcards. You understand various learning styles and pedagogical approaches to help users master any subject. You have access to current web information to create relevant and up-to-date quiz questions.

EDUCATIONAL EXPERTISE:
- Bloom's Taxonomy: Knowledge, Comprehension, Application, Analysis, Synthesis, Evaluation
- Multiple learning styles: Visual, Auditory, Kinesthetic, Reading/Writing
- Spaced repetition and active recall principles
- Adaptive difficulty progression
- Constructive feedback and explanation strategies
- Memory techniques and mnemonics
- Concept mapping and knowledge organization

QUIZ FORMATS & TYPES:
- Multiple choice with well-crafted distractors
- True/False with detailed explanations
- Fill-in-the-blank for key concepts
- Short answer and essay questions
- Matching exercises for associations
- Ordering/Sequencing for processes
- Case studies and scenario-based questions
- Image-based questions for visual learning

SUBJECT MATTER COVERAGE:
- STEM: Math, Science, Technology, Engineering
- Humanities: History, Literature, Philosophy, Arts
- Languages: Vocabulary, Grammar, Comprehension
- Professional: Business, Medicine, Law, Trades
- Life Skills: Personal Finance, Health, Cooking
- Hobbies: Sports, Games, Music, Crafts
- Test Prep: SAT, GRE, Professional Certifications
- Current Events: News, Technology trends, Recent discoveries

DIFFICULTY ADAPTATION:
- Beginner: Basic concepts and definitions
- Intermediate: Application and analysis
- Advanced: Synthesis and critical thinking
- Expert: Complex problem-solving and evaluation
- Adaptive progression based on performance

FEEDBACK & EXPLANATION:
- Immediate feedback for each answer
- Detailed explanations for correct answers
- Analysis of why wrong answers are incorrect
- Additional context and related concepts
- Study tips and memory aids
- Connections to real-world applications
- Recommendations for further study

QUIZ CREATION PROCESS:
1. Identify learning objectives and key concepts
2. Use web search results when available for current information
3. Determine appropriate question types and difficulty
4. Create engaging, clear, and unambiguous questions
5. Develop plausible but clearly incorrect distractors
6. Provide comprehensive explanations and context
7. Suggest follow-up questions or related topics

INTERACTIVE FEATURES:
- Progressive difficulty based on performance
- Personalized study recommendations
- Weak area identification and reinforcement
- Spaced repetition scheduling
- Progress tracking and analytics
- Collaborative learning suggestions
- Integration of current web information for relevancy

WEB INFORMATION INTEGRATION:
- When web search results are provided, incorporate current and accurate information
- Create quiz questions based on recent developments or current facts
- Use web sources to verify information and provide up-to-date context
- Cite sources when using specific information from web searches

Always make learning engaging, accessible, and pedagogically sound. Encourage curiosity and deeper understanding beyond memorization. When web information is available, use it to create more relevant and current quiz questions.
"""
    
    def get_system_prompt(self):
        return self._system_prompt
    
    def get_agent_name(self):
        return "Quiz Agent"
    
    def get_prompt_text(self):
        return "Request a quiz or flashcard on any topic, or ask for learning strategies"
    
    def prepare_prompt(self, user_message):
        """Prepare the prompt with web search results if relevant"""
        # Keywords that suggest the user wants current/recent information
        current_keywords = [
            'recent', 'latest', 'current', 'new', 'today', 'this year', 'now',
            'contemporary', 'modern', 'up-to-date', '2024', '2025', 'trending',
            'breaking', 'fresh', 'updated', 'present day', 'nowadays'
        ]
        
        # Topics that often benefit from web search
        web_search_topics = [
            'news', 'technology', 'science', 'politics', 'economics', 
            'sports', 'entertainment', 'health', 'environment', 'business',
            'social media', 'ai', 'artificial intelligence', 'climate',
            'covid', 'pandemic', 'vaccine', 'election', 'war', 'conflict'
        ]
        
        user_lower = user_message.lower()
        
        # Check if user explicitly asks for current information or topics that benefit from web search
        should_search = (
            any(keyword in user_lower for keyword in current_keywords) or
            any(topic in user_lower for topic in web_search_topics) or
            'web' in user_lower or 'internet' in user_lower or 'search' in user_lower
        )
        
        if should_search:
            # Set custom loading message for web search
            self.set_loading_message("Searching for current information...")
            
            # Extract the main topic for searching
            search_query = user_message
            
            # Try to clean up the search query
            if 'quiz' in user_lower:
                # Extract the topic after 'quiz on' or similar patterns
                import re
                patterns = [
                    r'quiz (?:me )?(?:on |about )(.*?)(?:\?|$)',
                    r'create (?:a )?quiz (?:on |about )(.*?)(?:\?|$)',
                    r'make (?:a )?quiz (?:on |about )(.*?)(?:\?|$)',
                    r'questions? (?:on |about )(.*?)(?:\?|$)'
                ]
                for pattern in patterns:
                    match = re.search(pattern, user_lower)
                    if match:
                        search_query = match.group(1).strip()
                        break
            
            print(f"Searching web for current information on: {search_query}")
            web_results = search_web(search_query)
            
            # Update loading message for quiz generation
            self.set_loading_message("Creating quiz questions...")
            
            if web_results:
                # Format web information for the prompt
                web_info = "\n\nCURRENT WEB INFORMATION:\n"
                for i, result in enumerate(web_results, 1):
                    web_info += f"\n{i}. {result['title']}:\n{result['content']}\n"
                    if result['url']:
                        web_info += f"Source: {result['url']}\n"
                
                web_info += "\nPlease use this current information to create relevant and up-to-date quiz questions when appropriate.\n"
                
                return user_message + web_info
        else:
            # Set loading message for regular quiz generation
            self.set_loading_message("Creating quiz questions...")
        
        return user_message


def main():
    """CLI entry point for quiz agent"""
    agent = QuizAgent()
    agent.run_cli()


if __name__ == "__main__":
    main()
