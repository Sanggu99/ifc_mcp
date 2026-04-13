import requests
import json

def test_chat():
    url = "http://localhost:8000/api/chat"
    payload = {
        "message": "안녕",
        "history": []
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat()
