import requests

LOCALHOST = "http://127.0.0.1:5000"

request = requests.post(LOCALHOST + "/user/login", json={"name": "Slungan", "password": "12345678"})
token = request.json()["access_token"]


create_event = requests.post("https://4323-213-100-200-167.eu.ngrok.io" + "/event/create", json={"name": "test_22", "description": "test_description22"},
                            headers={"Authorization": f"Bearer {token}"})

print(create_event.text)