import requests
import json

def test_email_count():
    url = "http://127.0.0.1:8000/chat"
    payload = {
        "session_id": "test_verification_session",
        "message": "how many new emails i've received",
        "context": {"root_path": "d:/coremind"}
    }
    
    print(f"Sending request: {payload['message']}")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("\nResponse:")
        print(json.dumps(result, indent=2))
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    test_email_count()
