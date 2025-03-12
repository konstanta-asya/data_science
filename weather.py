import datetime as dt
import json
import requests
from flask import Flask, jsonify, request

API_TOKEN = ""

WEATHER_API_KEY = ""
MISTRAL_API_KEY = ""

WEATHER_API_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

app = Flask(__name__)

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def get_weather(region: str, date: str):
    url = f"{WEATHER_API_URL}/{region}/{date}?unitGroup=metric&key={WEATHER_API_KEY}&contentType=json"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise InvalidUsage("Error fetching weather data", status_code=response.status_code)
    
    weather_data = response.json()
    
    if "days" not in weather_data or not weather_data["days"]:
        raise InvalidUsage("No weather data available for this date", status_code=404)
    
    day_data = weather_data["days"][0]
    
    return {
        "temp_c": day_data.get("temp", "N/A"),
        "wind_kph": day_data.get("windspeed", "N/A"),
        "pressure_mb": day_data.get("pressure", "N/A"),
        "humidity": day_data.get("humidity", "N/A"),
        "cloudcover": day_data.get("cloudcover", "N/A"),
        "conditions": day_data.get("conditions", "N/A"),
        "precip": day_data.get("precip", "N/A"),
    }


def get_ai_recommendation(weather_data):
    prompt = f"""
    На основі цієї погоди:
    - Температура: {weather_data["temp_c"]}°C
    - Вітер: {weather_data["wind_kph"]} км/год
    - Вологість: {weather_data["humidity"]}%
    - Умови: {weather_data["conditions"]}

    Дай рекомендації щодо обробки саду:
    Чи можна в цей день обробляти сад? 
    Чи можна оприскувати дерева від хвороб і шкідників?
    Давай коротку відповідь.
    """

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistral-tiny",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150
    }

    response = requests.post(MISTRAL_API_URL, headers=headers, json=data)

    if response.status_code != 200:
        raise InvalidUsage(f"Error fetching AI recommendation: {response.text}", status_code=response.status_code)

    ai_response = response.json()
    return ai_response["choices"][0]["message"]["content"]

@app.route("/")
def home_page():
    return "<p><h2>weather service</h2></p>"

@app.route("/ai_recommendation", methods=["POST"])
def ai_recommendation_endpoint():
    json_data = request.get_json()

    if json_data.get("token") is None:
        raise InvalidUsage("Token is required", status_code=400)

    token = json_data.get("token")
    if token != API_TOKEN:
        raise InvalidUsage("Wrong API token", status_code=403)

    region = json_data.get("location")
    date = json_data.get("date")
    requester_name = json_data.get("requester_name")

    if not region or not date or not requester_name:
        raise InvalidUsage("Location, date, and requester_name are required", status_code=400)

    weather = get_weather(region, date)
    recommendation = get_ai_recommendation(weather)

    return jsonify({
        "requester_name": requester_name,
        "location": region,
        "date": date,
        "weather": weather,
        "recommendation": recommendation
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
