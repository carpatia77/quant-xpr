import requests
import json

url = 'http://127.0.0.1:8000/v1/upload/options/PETR4'
headers = {'X-API-Key': 'test_key'}
files = {'file': ('dummy_options.csv', open('dummy_options.csv', 'rb'), 'text/csv')}

print(f"Sending POST to {url}...")
try:
    response = requests.post(url, headers=headers, files=files)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
