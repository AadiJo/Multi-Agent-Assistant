# Handle both relative and absolute imports
try:
    from .base import BaseAgent
except ImportError:
    from base import BaseAgent

import requests
import json
import yfinance as yf
from datetime import datetime, timedelta


class StockAgent(BaseAgent):
    """Financial assistant agent with real-time stock data"""
    
    def get_system_prompt(self):
        return """
You are an expert financial advisor and stock market analyst with access to REAL-TIME market data. You provide comprehensive investment guidance, market analysis, and financial education using current, accurate stock prices and market information.

CAPABILITIES:
- Real-time stock prices from Yahoo Finance
- Current market caps and trading volumes
- Daily price changes and percentage movements
- Technical analysis including price trends and momentum
- Fundamental analysis using live market data
- Portfolio diversification strategies
- Risk assessment and management advice
- Market sector analysis and trends
- Economic indicators impact on markets
- Investment strategies for different risk profiles

ANALYSIS APPROACH:
- Always reference CURRENT, REAL market data when available
- Provide both technical and fundamental perspectives based on live data
- Consider current market volatility and recent trends
- Explain reasoning behind recommendations with actual numbers
- Include risk factors and potential downsides
- Suggest position sizing and timing considerations
- Reference relevant economic factors affecting the market

INVESTMENT PHILOSOPHY:
- Emphasize long-term wealth building over speculation
- Stress the importance of diversification
- Explain risk vs. reward trade-offs clearly with real examples
- Recommend dollar-cost averaging for regular investors
- Advocate for emergency funds before investing
- Suggest low-cost index funds for beginners
- Warn about common investment mistakes

COMMUNICATION STYLE:
- Use clear, jargon-free explanations
- Provide specific, actionable advice with current data
- Include relevant numbers and percentages from live market data
- Explain complex concepts in simple terms
- Always include appropriate disclaimers
- End with a clear recommendation or next step

IMPORTANT: Always include a disclaimer that this is not personalized financial advice and users should consult with qualified financial advisors for their specific situations. All data is sourced from Yahoo Finance and reflects the most recent available market information.
"""
    
    def prepare_prompt(self, user_message):
        # Set custom loading message for market data fetching
        self.set_loading_message("Fetching market data...")
        
        # Extract stock symbols from user message if any
        market_data = self._get_market_overview()
        
        # Update loading message for specific stock analysis
        self.set_loading_message("Analyzing stock information...")
        
        stock_data = self._extract_and_fetch_stocks(user_message)
        
        # Set final loading message for AI processing
        self.set_loading_message("Preparing financial analysis...")
        
        context = f"""
CURRENT MARKET OVERVIEW:
{market_data}

SPECIFIC STOCK DATA:
{stock_data}

Current Date: {datetime.now().strftime('%Y-%m-%d')}
Market Hours: US markets trade 9:30 AM - 4:00 PM ET

User Question: {user_message}
"""
        return context
    
    def _get_market_overview(self):
        """Get general market overview"""
        try:
            # Using a free API for market overview (Alpha Vantage alternative)
            # You can replace this with your preferred financial data API
            symbols = ['SPY', 'QQQ', 'IWM']  # S&P 500, NASDAQ, Russell 2000 ETFs
            overview = "Market ETF Performance:\n"
            
            for symbol in symbols:
                data = self._fetch_stock_data(symbol)
                if data:
                    overview += f"- {symbol}: ${data['price']:.2f} ({data['change']:+.2f}% today)\n"
                else:
                    overview += f"- {symbol}: Data unavailable\n"
            
            return overview
        except Exception:
            return "Market data temporarily unavailable."
    
    def _extract_and_fetch_stocks(self, message):
        """Extract potential stock symbols and fetch their data"""
        import re
        
        # Common stock symbols (you can expand this)
        common_stocks = {
            'apple': 'AAPL', 'microsoft': 'MSFT', 'google': 'GOOGL', 'alphabet': 'GOOGL',
            'amazon': 'AMZN', 'tesla': 'TSLA', 'meta': 'META', 'facebook': 'META',
            'netflix': 'NFLX', 'nvidia': 'NVDA', 'amd': 'AMD', 'intel': 'INTC',
            'disney': 'DIS', 'coca cola': 'KO', 'pepsi': 'PEP', 'walmart': 'WMT',
            'visa': 'V', 'mastercard': 'MA', 'jpmorgan': 'JPM', 'goldman': 'GS'
        }
        
        # Look for stock symbols in the message
        symbols = set()
        message_lower = message.lower()
        
        # Check for company names
        for name, symbol in common_stocks.items():
            if name in message_lower:
                symbols.add(symbol)
        
        # Look for explicit symbols (e.g., AAPL, TSLA)
        symbol_pattern = r'\b[A-Z]{1,5}\b'
        potential_symbols = re.findall(symbol_pattern, message.upper())
        symbols.update(potential_symbols)
        
        # Fetch data for found symbols
        stock_info = ""
        for symbol in list(symbols)[:5]:  # Limit to 5 stocks to avoid API overload
            data = self._fetch_stock_data(symbol)
            if data:
                stock_info += f"""
{symbol} - {data.get('name', 'N/A')}:
- Price: ${data['price']:.2f}
- Change: {data['change']:+.2f}% today
- Volume: {data.get('volume', 'N/A')}
- Market Cap: {data.get('market_cap', 'N/A')}
"""
        
        return stock_info if stock_info else "No specific stock data requested."
    
    def _fetch_stock_data(self, symbol):
        """Fetch real stock data using yfinance"""
        try:
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            # Get current data
            info = ticker.info
            hist = ticker.history(period="2d")  # Get last 2 days to calculate change
            
            if hist.empty or len(hist) < 1:
                return None
            
            # Get current price (latest close)
            current_price = hist['Close'].iloc[-1]
            
            # Calculate daily change
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                change_percent = ((current_price - prev_close) / prev_close) * 100
            else:
                change_percent = 0.0
            
            # Format volume and market cap
            volume = hist['Volume'].iloc[-1] if not hist['Volume'].empty else 0
            volume_formatted = self._format_number(volume)
            
            market_cap = info.get('marketCap', 0)
            market_cap_formatted = self._format_number(market_cap)
            
            return {
                'price': float(current_price),
                'change': float(change_percent),
                'volume': volume_formatted,
                'market_cap': market_cap_formatted,
                'name': info.get('longName', info.get('shortName', symbol))
            }
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def _format_number(self, num):
        """Format large numbers into readable format"""
        if num >= 1e12:
            return f"{num/1e12:.1f}T"
        elif num >= 1e9:
            return f"{num/1e9:.1f}B"
        elif num >= 1e6:
            return f"{num/1e6:.1f}M"
        elif num >= 1e3:
            return f"{num/1e3:.1f}K"
        else:
            return f"{num:,.0f}"
    
    def get_agent_name(self):
        return "Stock Agent"
    
    def get_prompt_text(self):
        return "Ask about stocks, investments, or financial advice"


def main():
    """CLI entry point for stock agent"""
    agent = StockAgent()
    agent.run_cli()


if __name__ == "__main__":
    main()
