import os
import pytest
from app import create_app, db
import tempfile


LOCALHOST = "http://127.0.0.1:5000"


@pytest.fixture(scope='session')
def app():
    # Use a separate testing configuration file
    app = create_app(True)

    # Create the database and apply the schema
    with app.app_context():
        db.drop_all()
        db.create_all()

        yield app


@pytest.fixture(scope='session')
def client(app):
    return app.test_client()


@pytest.fixture(scope='session')
def token(client):
    response = client.post(LOCALHOST + '/user/register',
                           json={"name": "kacper", "password": "skåne"})
    response = client.post(LOCALHOST + '/user/login',
                           json={"name": "kacper", "password": "skåne"})
    return response.json['access_token']


def test_api_returns_hello_world(client):
    response = client.get(LOCALHOST + '/hello')
    assert response.status_code == 200
    assert response.get_data(as_text=True) == 'Hello, World!'


def test_register(client):
    response = client.post(LOCALHOST + '/user/register',
                           json={"name": "test", "password": "test"})
    assert response.status_code == 200
    assert response.json['response'] == "User created"


def test_login_successful(client):
    print("test_login_successful")
    response = client.post(LOCALHOST + '/user/login',
                           json={"name": "test", "password": "test"})
    assert response.status_code == 200
    assert 'access_token' in response.json


def test_create_event(client, token):
    response = client.post('/event/create', json={"name": "test_event", "description": "test_description"},
                           headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json['response'] == "Event created"


def test_get_all_events(client, token):
    response = client.get(
        '/event/all', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_get_nonexistent_event(client, token):
    response = client.get(
        '/event/fakevent', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
    assert response.json['response'] == "Event not found"


def test_get_event(client, token):
    response = client.get('/event/test_event',
                          headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json['name'] == "test_event"
    assert response.json['description'] == "test_description"
    assert response.json['creator'] == "kacper"
    assert response.json['members'] == []
    assert response.json['messages'] == []


def test_join_event(client, token):
    response = client.post('event/join/test_event',
                           headers={'Authorization': f'Bearer {token}'})

    assert response.json['response'] == "Joined event"
    assert response.status_code == 200

    event = client.get('/event/test_event',
                       headers={'Authorization': f'Bearer {token}'})

    assert event.json['members'] == ['kacper']


def test_join_again(client, token):
    response = client.post('event/join/test_event',
                            headers={'Authorization': f'Bearer {token}'})

    assert response.json['response'] == "User already in event"
    assert response.status_code == 202

    event = client.get('/event/test_event',
                       headers={'Authorization': f'Bearer {token}'})

    assert event.json['members'] == ['kacper']


def test_send_message(client, token):
    response = client.post('/event/send/test_event', json={"text": "test_message"},
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json['response'] == "Message sent"

    event = client.get('/event/test_event',
                       headers={'Authorization': f'Bearer {token}'})
    assert event.json['messages'][0]['text'] == "test_message"
    assert event.json['messages'][0]['author'] == "kacper"


def test_send_message_fail(client, token):
    response = client.post('/event/send/fakevent', json={"text": "test_message"},
                           headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
    assert response.json['response'] == "Event not found"


def test_get_messages(client, token):
    response = client.get('/event/messages/test_event',
                          headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_get_message(client, token):
    response = client.get('/event/message/test_event/1',
                          headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 200
    assert response.json['text'] == "test_message"
    assert response.json['author'] == "kacper"



def test_leave_event(client, token):
    response = client.post('/event/leave/test_event',
                           headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 200
    assert response.json['response'] == 'Left event'



def test_leave_event_fail(client, token):
    response = client.post('/event/leave/test_event',
                           headers={'Authorization': f'Bearer {token}'})
    
    assert response.status_code == 404
    assert response.json['response'] == 'User not in event'
    


def test_register_existing_user(client):
    response = client.post(LOCALHOST + '/user/register',
                           json={"name": "test", "password": "test"})
    response = client.post(LOCALHOST + '/user/register',
                           json={"name": "test", "password": "test"})
    assert response.status_code == 400
    assert response.json['response'] == "Username already exists"


def test_login_nonexistent_user(client):
    response = client.post(LOCALHOST + '/user/login',
                           json={"name": "fakeuser", "password": "test"})
    assert response.status_code == 401
    assert response.json['response'] == "Wrong username or password"


def test_login_wrong_password(client):
    response = client.post(LOCALHOST + '/user/login',
                           json={"name": "test", "password": "wrongpassword"})
    assert response.status_code == 401
    assert response.json['response'] == "Wrong username or password"


def test_get_nonexistent_user(client, token):
    response = client.get(
        '/user/fakeuser', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
    assert response.json['response'] == "User not found"


def test_get_user(client, token):
    response = client.get(
        '/user/test', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json['name'] == "test"


def test_logout(client, token):
    response = client.post(
        '/user/logout', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json['response'] == "Logout successful"
