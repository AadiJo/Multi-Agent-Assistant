import requests
import subprocess
import time
import socket
import sys
import json

# Handle both relative and absolute imports
try:
    from .base import BaseAgent
except ImportError:
    from base import BaseAgent

# Color codes for terminal output
class Colors:
    LIGHT_BLUE = '\033[94m'
    RED = '\033[91m'
    RESET = '\033[0m'

OLLAMA_MODEL = "mistral"

# Cache for weather data
_location_cache = None
_weather_cache = None
_cache_time = None


def ensure_ollama_running():
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
    print(f"Checking if model '{model}' is available...")
    models = requests.get("http://localhost:11434/api/tags").json()
    if not any(model in m["name"] for m in models.get("models", [])):
        print(f"Pulling model '{model}'...")
        subprocess.run(["ollama", "pull", model], check=True)


def get_location():
    try:
        response = requests.get("http://ip-api.com/json/").json()
        return {
            "city": response["city"],
            "region": response["regionName"],
            "country": response["country"],
            "lat": response["lat"],
            "lon": response["lon"]
        }
    except:
        print("Could not fetch your location.")
        return None


def get_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,precipitation,weather_code,wind_speed_10m,relative_humidity_2m"
        f"&hourly=temperature_2m,precipitation,weather_code,wind_speed_10m,relative_humidity_2m"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
        f"&forecast_days=3&timezone=auto&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
    )
    try:
        return requests.get(url).json()
    except:
        print("Could not get weather data.")
        return None


def get_cached_weather_data():
    """Get cached weather data or fetch new if cache is stale"""
    global _location_cache, _weather_cache, _cache_time
    
    current_time = time.time()
    # Cache for 10 minutes
    if (_cache_time is None or 
        current_time - _cache_time > 600 or 
        _location_cache is None or 
        _weather_cache is None):
        
        print("Fetching fresh weather data...")
        _location_cache = get_location()
        if _location_cache:
            _weather_cache = get_weather(_location_cache['lat'], _location_cache['lon'])
            _cache_time = current_time
    
    return _location_cache, _weather_cache


class WeatherAgent(BaseAgent):
    """Weather agent that provides detailed weather information"""
    
    def get_system_prompt(self):
        return """
You are a helpful weather assistant that analyzes comprehensive weather data to answer user questions.

AVAILABLE DATA:
- Current weather conditions (temperature in °F, precipitation in inches, weather code, wind speed in mph, humidity %)
- Hourly forecasts for the next 72 hours (3 days) with the same parameters
- Daily summaries for the next 3 days (min/max temperature in °F, total precipitation in inches, weather code)
- All times are in the user's local timezone

WEATHER CODES (key ones):
0 = Clear sky, 1-3 = Partly cloudy, 45-48 = Fog, 51-67 = Rain (light to heavy), 
71-86 = Snow, 95-99 = Thunderstorms

YOUR TASK:
- Analyze the relevant time periods based on the user's question
- For "today" questions: use current + today's hourly/daily data
- For "tomorrow" questions: use tomorrow's hourly/daily data  
- For "this afternoon/evening" questions: focus on relevant hourly data
- For "this week" questions: use daily summaries
- Provide specific, actionable advice based on the data
- Mention specific times, temperatures in Fahrenheit, and conditions when relevant
- Use Fahrenheit for all temperature references
- Directly answer the user's question based on the data provided, and don't give anything unnecessary.
- End your response with a clear action item or conclusion on a new line
- When the user gives greetings or small talk, don't answer with weather data, just acknowledge their greeting.

Be conversational but precise. Always ground your answers in the actual data provided.
"""
    
    def prepare_prompt(self, user_message):
        # Set custom loading message for weather data fetching
        self.set_loading_message("Fetching weather data...")
        
        location, weather = get_cached_weather_data()
        if not location or not weather:
            return "I'm sorry, I couldn't fetch weather data at the moment."
        
        # Reset to default message for AI processing
        self.set_loading_message("Analyzing weather conditions...")
        
        location_str = f"{location['city']}, {location['region']}, {location['country']}"
        
        # Format current conditions
        current = weather['current']
        current_summary = (
            f"Current: {current['temperature_2m']}°F, "
            f"{current['precipitation']}in precip, "
            f"wind {current['wind_speed_10m']}mph, "
            f"{current['relative_humidity_2m']}% humidity, "
            f"weather code {current['weather_code']}"
        )
        
        # Format hourly data (next 24-48 hours for context)
        hourly = weather['hourly']
        hourly_summary = "HOURLY FORECAST (next 48 hours):\n"
        for i in range(0, min(48, len(hourly['time']))):
            time_str = hourly['time'][i]
            temp = hourly['temperature_2m'][i]
            precip = hourly['precipitation'][i] 
            code = hourly['weather_code'][i]
            hourly_summary += f"{time_str}: {temp}°F, {precip}in, code {code}\n"
        
        # Format daily data
        daily = weather['daily']
        daily_summary = "DAILY FORECAST:\n"
        for i in range(len(daily['time'])):
            date = daily['time'][i]
            temp_max = daily['temperature_2m_max'][i]
            temp_min = daily['temperature_2m_min'][i]
            precip = daily['precipitation_sum'][i]
            code = daily['weather_code'][i]
            daily_summary += f"{date}: {temp_min}°F - {temp_max}°F, {precip}in total, code {code}\n"

        return f"""
Location: {location_str}
{current_summary}

{hourly_summary}

{daily_summary}

User question: {user_message}
"""

    def get_agent_name(self):
        return "Weather Agent"
    
    def get_prompt_text(self):
        return "Ask a weather-related question"
    
    def initialize(self):
        """Initialize weather data for CLI mode"""
        location = get_location()
        if not location:
            return False

        weather = get_weather(location['lat'], location['lon'])
        if not weather:
            return False

        print(f"Detected location: {location['city']}, {location['region']}, {location['country']}")
        print("Weather data loaded.")
        return True


def main():
    """CLI entry point for weather agent"""
    agent = WeatherAgent()
    agent.run_cli()


if __name__ == "__main__":
    main()
