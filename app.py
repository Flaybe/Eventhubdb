from flask import Flask
from flask import request
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    get_jwt_identity,
    get_jwt_header,
    get_jwt
)


app = Flask(__name__)
bcrypt = Bcrypt(app)

if not 'WEBSITE_HOSTNAME' in os.environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'
    app.config.from_prefixed_env()

else:
    DATABASE_URI = 'postgresql+psycopg2://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
        dbuser=os.environ['DBUSER'],
        dbpass=os.environ['DBPASS'],
        dbhost=os.environ['DBHOST'] + ".postgres.database.azure.com",
        dbname=os.environ['DBNAME'])

    app.config['JWT_SECRET_KEY'] = os.environ['DBSECRET']
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI

# sätter tiden för hur länge en token är giltig
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 12000


jwt = JWTManager(app)
db = SQLAlchemy(app)

#### TABLES ####

members = db.Table('members',
                   db.Column('user_id', db.Integer, db.ForeignKey('User.id')),
                   db.Column('event_id', db.Integer, db.ForeignKey('Event.id')))

'''tillfällig, får se om det är värt att implementera
friends = db.Table("friends",
                   db.Column("user_id", db.Integer, db.ForeignKey("User.id")),
                   db.Column("user_id", db.Integer, db.ForeignKey("User.id")))
'''
###### CLASSES ##########


class Event(db.Model):
    '''
    Event har columner för id, namn, beskrivning och en many-many relation till User
    eftersom att en användare kan vara med i flera events och ett event kan ha flera
    användare.

    Event har också en one-many relation till Message eftersom att ett event kan ha flera
    meddelanden.

    Event har också en metod som returnerar en dictionary med alla attribut för att
    underlätta för frontend att hantera datan.
    '''
    __tablename__ = 'Event'

    id = db.Column(db.Integer, primary_key=True)
    users_in_event = db.relationship(
        "User", secondary='members', back_populates="users_events")
    name = db.Column(db.String(250), unique=True)
    description = db.Column(db.String(250))
    messages = db.relationship('Message', backref='event')
    creator = db.Column(db.String(60), db.ForeignKey("User.name"))

    def to_dict(self):
        output = {}
        output['id'] = self.id
        output['name'] = self.id
        output['description'] = self.description
        output['members'] = [user.id for user in self.users_in_event]
        output['messages'] = [message.to_dict() for message in self.messages]


class User(db.Model):
    '''
    User har columner för id, namn, lösenord och en many-many relation till Event
    eftersom att en användare kan vara med i flera events och ett event kan ha flera
    användare.

    User har också en one-many relation till Message eftersom att en användare kan
    skriva flera meddelanden.

    User har också en metod som returnerar en dictionary med alla attribut för att
    underlätta för frontend att hantera datan.

    Users lösenord hashas med bcrypt innan det sparas i databasen.
    '''
    __tablename__ = 'User'

    id = db.Column(db.Integer, primary_key=True)
    users_events = db.relationship(
        "Event", secondary='members', back_populates='users_in_event')
    messages = db.relationship('Message', backref='user')
    events = db.relationship('Event', backref='user_id')

    name = db.Column(db.String(60), unique=True)
    password = db.Column(db.String(200), nullable=False)

    '''
    sent_requests = db.relationship("User", bakcref="user")
    recieved_requests = db.Column(db.Integer, db.ForeignKey("User.id"))
    '''

    def __init__(self, name, password):
        self.name = name
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")


class Message(db.Model):
    '''
    Message har columner för id, text, user_id och event_id.

    Message har också en metod som returnerar en dictionary med alla attribut för att
    underlätta för frontend att hantera datan.
    '''
    __tablename__ = 'Message'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250))
    username = db.Column(db.Integer, db.ForeignKey('User.name'))
    event_id = db.Column(db.Integer, db.ForeignKey('Event.id'))

    def to_dict(self):
        output = {}
        output["id"] = self.id
        output["text"] = self.text
        output['author'] = self.username
        output['event_id'] = self.event_id
        return output


class JWT_blocklist(db.Model):
    '''
    JWT_blocklist har columner för id och revoked_token.

    revoked_token är en sträng som är en JWT token som har blivit utloggad.
    '''
    __tablename__ = "JWT_blocklist"
    id = db.Column(db.Integer, primary_key=True)
    revoked_token = db.Column("token", db.String(700), unique=True)


###### ROUTES ##########
'''
Lista på alla routes som finns:

# AUTHENTICATION
/user/register : registrerar en ny användare
/user/login : loggar in en användare
/user/logout : loggar ut en användare

# EVENTS
/event/create : skapar ett nytt event
/event/<string:event_name> : returnerar ett event med ett specifikt namn
/events : returnerar en lista med alla events

# MESSAGES
/message/<int:event_id>/<int:user_id> : postar ett meddelande i ett event
/messages/<int:event_id> : returnerar alla meddelanden i ett event

# USERS
/users : returnerar en lista med alla användare
/user/<int:user_id> : returnerar en användare med ett specifikt id
/user/<int:user_id>/events : returnerar en lista med alla events som en användare är med i

TODO:
/event/members
/user/friends

'''


########### DENNA KOD ÄR FÖR AUTHENTICATION ################################

@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    '''
    Denna funktion kollar om en JWT token finns i databasen och returnerar True
    om den finns och False om den inte finns.

    Den används av flask_jwt_extended för att kolla om en token är utloggad.
    Används i @jwt_required() dekoratorn.
    '''
    jti = jwt_payload["jti"]
    is_revoked = JWT_blocklist.query.filter_by(revoked_token=jti).first()
    if is_revoked is None:
        return False
    return True


@app.route('/user/logout', methods=['POST'])
@jwt_required()
def logout():
    '''
    Kräver att användaren är inloggad.

    Denna funktion lägger till en JWT token i databasen i tabellen JWT_blocklist
    och returnerar en JSON response med ett meddelande.
    '''
    jti = get_jwt()['jti']
    revoked = JWT_blocklist(revoked_token=jti)
    db.session.add(revoked)
    db.session.commit()

    return jsonify({'message': 'logged out'}), 200


@app.route("/user/register", methods=['POST'])
def register():
    '''
    Denna funktion tar emot en JSON request med namn och lösenord och skapar en ny
    användare i databasen om namnet inte redan finns.

    Om namnet redan finns returneras en JSON response med ett meddelande och status
    400.

    Om namnet inte redan finns returneras en JSON response med ett meddelande och
    status 200.
    '''
    data = request.json
    name = data["name"]
    password = data["password"]
    user = User.query.filter_by(name=name).first()

    if user is None:
        user = User(name=name, password=password)
        db.session.add(user)
        db.session.commit()
        return jsonify({"message": "User created"}), 200

    return jsonify({"message": "Username taken"}), 400


@app.route("/user/login", methods=['POST'])
def login():
    '''
    Denna funktion tar emot en JSON request med namn och lösenord och returnerar en
    JWT token om namnet och lösenordet stämmer.

    Om namnet eller lösenordet inte stämmer returneras en JSON response med ett
    meddelande och status 400.

    Om namnet och lösenordet stämmer returneras en JSON response med en JWT token
    och status 200.
    '''
    data = request.json
    password = data["password"]
    name = data["name"]
    user = User.query.filter_by(name=name).first()
    if user is None:
        return jsonify({'message': 'Wrong password'}), 400

    elif not bcrypt.check_password_hash(user.password, password):
        return jsonify({'message': 'Wrong password'}), 400

    token = create_access_token(identity=user.name, expires_delta=None)
    return jsonify(access_token=token), 200


############### ROUTES FÖR EVENT #########################
#
# Skapa event
# Visa alla event
# Visa event efter id

# TODO
# Uppdatera event
# Ta bort event


@app.route('/event/create', methods=['POST'])
@jwt_required()
def create_event():
    '''
    Kräver att användaren är inloggad.

    Denna funktion tar emot en JSON request med namn och beskrivning och skapar ett
    nytt event i databasen om namnet inte redan finns.

    Om namnet redan finns returneras en JSON response med ett meddelande och status
    400.

    Om namnet inte redan finns returneras en JSON response med ett meddelande och
    status 200.
    '''
    data = request.json
    name = data['name']
    description = data['description']

    # check if name is taken
    events = Event.query.filter_by(name=name).first()
    if events != None:
        return jsonify({"response": "Name already taken"}), 400

    # Skapar eventet
    event = Event(name=name, description=description,
                  creator=get_jwt_identity())
    db.session.add(event)
    db.session.commit()
    return jsonify({'response': 'Event created'}), 200


@app.route('/event/<Name>', methods=['GET'])
@jwt_required()
def show_event(Name):
    '''
    Kräver att användaren är inloggad.

    Denna funktion tar emot ett namn och returnerar ett event i json format om
    eventet finns i databasen.

    Om eventet inte finns i databasen returneras en JSON response med ett
    meddelande och status 404.

    Om eventet finns i databasen returneras en JSON response med eventet i json
    format och status 200.
    '''
    event = Event.query.filter_by(name=Name).first()
    if event != None:
        return jsonify(event.to_dict()), 200

    return jsonify({'response': 'Event not found'}), 404


@app.route('/events', methods=['GET'])
@jwt_required()
def show_events():
    '''
    Kräver att användaren är inloggad.

    Denna funktion returnerar alla event i databasen i json format.
    '''
    events = Event.query.filter_by().all()
    event_list = [event.to_dict() for event in events]
    return jsonify(event_list), 200


'''
@app.route('/event/users/<EventID>', methods=['GET'])
@jwt_required()
def show_users(EventID):
    
    users = User.query.filter_by(event_id=EventID).all()

    if users == None:
        return jsonify({'response': 'No users in event'}), 404

    user_list = [user.to_dict() for user in users]
    return jsonify(user_list), 200
'''


@app.route('/event/<EventID>', methods=['DELETE'])
@jwt_required()
def delete_event(EventID):

    event = Event.query.filter_by(id=EventID).first()

    # make sure the user is the creator of the event
    print(get_jwt_identity())
    print(event.creator)
    if event.creator != get_jwt_identity():
        return jsonify({'response': 'Not authorized'}), 401

    if event != None:
        db.session.delete(event)
        db.session.commit()
        return jsonify({'response': 'Event deleted'}), 200

    return jsonify({'response': 'Event not found'}), 404


# MESSAGE ROUTES ###############################3
#
# Create messages
#

@app.route('/message/<EventID>', methods=['POST'])
@jwt_required()
def post_message(EventID):
    '''
    Kräver att användaren är inloggad.

    Denna funktion tar emot en JSON request med text och skapar ett nytt medelande
    i databasen i ett event.

    Om eventet eller användaren inte finns i databasen returneras en JSON response
    med ett meddelande och status 404.

    Om eventet och användaren finns i databasen returneras en JSON response med ett
    meddelande och status 200.
    '''

    # Letar upp eventet
    event = Event.query.filter_by(id=EventID).first()
    user = User.query.filter_by(name=get_jwt_identity()).first()
    if user == None:
        return jsonify({'response': 'User not found'}), 404

    if event == None:
        return jsonify({'response': 'Event not found'}), 404

    # Första gången man skickar ett medelande i en chatt blir man en member
    if user.id not in event.users_in_event:
        event.users_in_event.append(user)
        db.session.add(event)

    data = request.json
    text = data['text']

    message = Message(text=text, username=user.name, event_id=EventID)
    event.messages.append(message)
    db.session.add(message)
    db.session.commit()

    return jsonify({'response': 'Message posted'}), 200


@app.route('/messages/<EventID>', methods=['GET'])
@jwt_required()
def show_messages(EventID):
    '''
    Kräver att användaren är inloggad.

    Denna funktion tar emot ett event id och returnerar alla medelanden i json
    format om eventet finns i databasen.

    Om eventet inte finns i databasen returneras en JSON response med ett
    meddelande och status 404.

    Om eventet finns i databasen returneras en JSON response med alla medelanden i
    json format och status 200.
    '''
    event = Event.query.filter_by(id=EventID).first()

    if event == None:
        return jsonify({'response': 'Event not found'}), 404

    message_list = [message.to_dict() for message in event.messages]
    return jsonify(message_list), 200


########## ROUTES FÖR USER #############################
#
# Visa alla användare
# Visa användare efter id
# Visa användarens event (medlem)

# TODO
# Visa användarens medelanden


@app.route('/users', methods=['GET'])
@jwt_required()
def show_users():
    '''
    Kräver att användaren är inloggad.

    Denna funktion returnerar alla användare i databasen i json format.
    '''
    users = User.query.filter_by().all()
    user_list = [user.to_dict() for user in users]
    return jsonify(user_list), 200


@app.route('/user/<UserID>', methods=['GET'])
@jwt_required()
def show_user(UserID):
    '''
    Kräver att användaren är inloggad.

    Denna funktion tar emot ett användar id och returnerar en användare i json
    format om användaren finns i databasen.

    Om användaren inte finns i databasen returneras en JSON response med ett
    meddelande och status 404.

    Om användaren finns i databasen returneras en JSON response med användaren i
    json format och status 200.
    '''
    user = User.query.filter_by(id=UserID).first()
    if user != None:
        return jsonify(user.to_dict()), 200

    return jsonify({'response': 'User not found'}), 404


@app.route('/user/<UserID>/events', methods=['GET'])
@jwt_required()
def show_user_events(UserID):
    '''
    Kräver att användaren är inloggad.

    Denna funktion tar emot ett användar id och returnerar alla event som
    användaren är med i i json format om användaren finns i databasen.

    Om användaren inte finns i databasen returneras en JSON response med ett
    meddelande och status 404.

    Om användaren finns i databasen returneras en JSON response med alla event som
    användaren är med i i json format och status 200.
    '''
    user = User.query.filter_by(id=UserID).first()
    if user == None:
        return jsonify({'response': 'User not found'}), 404

    event_list = [event.to_dict() for event in user.events]
    return jsonify(event_list), 200


@app.route('/user/<UserID>/friend/<UserID2>', methods=['POST'])
@jwt_required()
def add_friend(UserID, UserID2):
    '''
    Kräver att användaren är inloggad.

    Denna funktion tar emot två användar id och lägger till användare 2 som
    vän till användare 1 om användarna finns i databasen.

    Om användarna inte finns i databasen returneras en JSON response med ett
    meddelande och status 404.

    Om användarna finns i databasen returneras en JSON response med ett meddelande
    och status 200.
    '''
    user = User.query.filter_by(id=UserID).first()
    user2 = User.query.filter_by(id=UserID2).first()

    if user == None or user2 == None:
        return jsonify({'response': 'User not found'}), 404

    user2.recieved_requests.append(user)
    db.session.add(user2)
    db.session.commit()
    return jsonify({'response': 'Friend added'}), 200


if __name__ == '__main__':
    app.run(debug=True)
