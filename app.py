import os
import requests

API_KEY = os.environ.get("API_KEY")

def fetch_data(user_input):
    # intentionally vulnerable — command injection surface
    os.system("curl " + user_input)

def get_weather():
    return requests.get("http://api.weather.com/data")