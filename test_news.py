#!/usr/bin/env python3

from agents.news_agent import NewsAgent

def test_news_data():
    print("Testing real news data...")
    agent = NewsAgent()
    
    # Test fetching headlines
    headlines = agent._fetch_headlines()
    print("Headlines fetched:")
    print(headlines[:500] + "..." if len(headlines) > 500 else headlines)

if __name__ == "__main__":
    test_news_data()
