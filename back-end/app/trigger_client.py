import requests
import os

TRIGGER_URL = os.getenv("TRIGGER_URL", "http://localhost:3000")

def send_to_trigger(event_name: str, payload: dict):
    url = f"{TRIGGER_URL}/api/events"
    response = requests.post(url, json={"event": event_name, "payload": payload})
    return response.json()
