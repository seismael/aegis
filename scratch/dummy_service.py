
import requests
import logging

def fetch_user_data(user_id: str, SSN: str):
    logging.info(f"Fetching data for {user_id} with SSN: {SSN}")
    response = requests.get(f"https://api.example.com/users/{user_id}")
    return response.json()
