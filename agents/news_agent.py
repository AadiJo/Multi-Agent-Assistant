import requests

# Handle both relative and absolute imports
try:
    from .base import BaseAgent
except ImportError:
    from base import BaseAgent


class NewsAgent(BaseAgent):
    """Advanced news analysis agent with comprehensive reporting capabilities"""
    
    def get_system_prompt(self):
        return """
You are an expert news analyst and journalist with deep knowledge of current events, media literacy, and global affairs. You provide comprehensive news analysis, context, and insights.

ANALYTICAL CAPABILITIES:
- Breaking down complex news stories into key points
- Providing historical context and background information
- Identifying potential bias and multiple perspectives
- Explaining the broader implications of news events
- Connecting related stories and trends
- Fact-checking and source verification guidance
- Media literacy education

ANALYSIS FRAMEWORK:
- WHO: Key players, stakeholders, and affected parties
- WHAT: Core facts and developments
- WHEN: Timeline and temporal context
- WHERE: Geographic scope and regional implications
- WHY: Underlying causes and motivations
- HOW: Mechanisms, processes, and methodologies
- SO WHAT: Significance, impact, and consequences

REPORTING STYLE:
- Present information objectively and factually
- Acknowledge uncertainty and ongoing developments
- Distinguish between confirmed facts and speculation
- Provide multiple viewpoints when appropriate
- Explain technical or specialized terminology
- Highlight potential long-term implications
- Suggest reliable sources for further reading

CRITICAL THINKING GUIDANCE:
- Help users evaluate source credibility
- Identify potential bias in reporting
- Distinguish between news, opinion, and analysis
- Explain how to verify information
- Discuss the importance of primary sources
- Warn about misinformation and propaganda

GLOBAL PERSPECTIVE:
- Consider international implications of events
- Explain cultural and political context
- Discuss how events affect different regions
- Provide comparative analysis with similar past events
- Address economic, social, and political impacts

Always encourage users to seek multiple sources and think critically about the information they consume.
"""
    
    def prepare_prompt(self, user_message):
        # Set custom loading message for news data fetching
        self.set_loading_message("Fetching latest news...")
        
        # Fetch current headlines
        headlines = self._fetch_headlines()
        
        # Update loading message for analysis
        self.set_loading_message("Analyzing news relevance...")
        
        # Check if user is asking about a specific topic
        topic_analysis = self._analyze_topic_relevance(user_message, headlines)
        
        # Set final loading message for AI processing
        self.set_loading_message("Preparing news analysis...")
        
        context = f"""
CURRENT TOP HEADLINES:
{headlines}

TOPIC ANALYSIS:
{topic_analysis}

MEDIA LITERACY REMINDER:
- Always verify information from multiple reliable sources
- Be aware of publication date and context
- Consider the source's potential bias and agenda
- Look for primary sources and official statements
- Distinguish between breaking news and confirmed facts

User Question: {user_message}
"""
        return context
    
    def _fetch_headlines(self):
        """Fetch and format current headlines from multiple sources"""
        try:
            # Try multiple free news sources
            headlines = self._try_newsapi() or self._try_rss_feeds() or self._fallback_headlines()
            return headlines
            
        except Exception as e:
            return f"News data temporarily unavailable. Error: {str(e)}"
    
    def _try_newsapi(self):
        """Try to fetch from NewsAPI (free tier)"""
        try:
            # Using NewsAPI free tier - replace with your API key if you have one
            # For now, using BBC RSS as an alternative
            url = "http://feeds.bbci.co.uk/news/rss.xml"
            return self._parse_rss_feed(url, "BBC News")
        except:
            return None
    
    def _try_rss_feeds(self):
        """Fetch headlines from RSS feeds"""
        try:
            import xml.etree.ElementTree as ET
            
            # List of reliable RSS feeds
            rss_sources = [
                ("http://feeds.bbci.co.uk/news/rss.xml", "BBC News"),
                ("https://rss.cnn.com/rss/edition.rss", "CNN"),
                ("https://feeds.npr.org/1001/rss.xml", "NPR"),
            ]
            
            all_headlines = ""
            article_count = 0
            
            for url, source_name in rss_sources:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        root = ET.fromstring(response.content)
                        items = root.findall('.//item')[:3]  # Get 3 items per source
                        
                        for item in items:
                            if article_count >= 8:  # Limit total articles
                                break
                            
                            title = item.find('title')
                            pub_date = item.find('pubDate')
                            
                            if title is not None:
                                article_count += 1
                                title_text = title.text if title.text else "No title"
                                date_text = pub_date.text if pub_date is not None else "Unknown date"
                                all_headlines += f"{article_count}. {title_text}\n   Source: {source_name} | Published: {date_text}\n\n"
                except:
                    continue
            
            return all_headlines if all_headlines else None
            
        except:
            return None
    
    def _parse_rss_feed(self, url, source_name):
        """Parse a single RSS feed"""
        try:
            import xml.etree.ElementTree as ET
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return None
                
            root = ET.fromstring(response.content)
            items = root.findall('.//item')[:8]  # Get top 8 items
            
            formatted_headlines = ""
            for i, item in enumerate(items, 1):
                title = item.find('title')
                pub_date = item.find('pubDate')
                
                if title is not None:
                    title_text = title.text if title.text else "No title"
                    date_text = pub_date.text if pub_date is not None else "Unknown date"
                    formatted_headlines += f"{i}. {title_text}\n   Source: {source_name} | Published: {date_text}\n\n"
            
            return formatted_headlines
            
        except Exception:
            return None
    
    def _fallback_headlines(self):
        """Fallback headlines when APIs are unavailable"""
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        return f"""
LIVE NEWS CURRENTLY UNAVAILABLE - Using fallback mode

NOTE: Real-time news data is temporarily unavailable. I can still provide:
- Analysis of general news topics and trends
- Context about ongoing global issues
- Media literacy guidance
- Help understanding news stories you share
- Background information on current events

Date: {current_date}

Please share a specific news story or topic you'd like me to analyze, or ask about general news trends and I'll provide informed analysis based on my knowledge.
"""
    
    def _analyze_topic_relevance(self, user_message, headlines):
        """Analyze if user question relates to current headlines"""
        user_lower = user_message.lower()
        keywords = user_lower.split()
        
        relevant_headlines = []
        for line in headlines.split('\n'):
            if any(keyword in line.lower() for keyword in keywords if len(keyword) > 3):
                relevant_headlines.append(line)
        
        if relevant_headlines:
            return f"Your question appears related to these current stories:\n" + "\n".join(relevant_headlines[:3])
        else:
            return "Your question doesn't directly relate to current top headlines. I'll provide analysis based on general knowledge and context."
    
    def get_agent_name(self):
        return "News Agent"
    
    def get_prompt_text(self):
        return "Ask about current news, analysis, or media literacy"


def main():
    """CLI entry point for news agent"""
    agent = NewsAgent()
    agent.run_cli()


if __name__ == "__main__":
    main()
