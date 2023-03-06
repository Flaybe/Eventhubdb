from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt


db = SQLAlchemy()
bcrypt = Bcrypt()

members = db.Table('members',
                   db.Column('user_id', db.Integer, db.ForeignKey('User.id')),
                   db.Column('event_id', db.Integer, db.ForeignKey('Event.id')))

###### CLASSES ##########


class Event(db.Model):
    '''
    Event har columner för id, namn, beskrivning, en many-many relation till User
    och en one-many relation till Message.

    To_dict() metod 
    '''
    __tablename__ = 'Event'

    id = db.Column(db.Integer, primary_key=True)
    users_in_event = db.relationship(
        "User", secondary='members', back_populates="users_events")
    name = db.Column(db.String(250), unique=True)
    description = db.Column(db.String(250))
    messages = db.relationship('Message', backref='eventname')
    creator = db.Column(db.String(60), db.ForeignKey("User.name"))

    def to_dict(self):
        output = {}
        output['id'] = self.id
        output['name'] = self.name
        output['description'] = self.description
        output['members'] = [user.name for user in self.users_in_event]
        output['messages'] = [message.to_dict() for message in self.messages]
        output['creator'] = self.creator
        return output


class User(db.Model):
    '''
    User har columner för id, namn, lösenord och en many-many relation till Event
    one-many relation till Message
    to_dict() metod

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

    def to_dict(self):
        output = {}
        output['id'] = self.id
        output['name'] = self.name
        output['events'] = [event.id for event in self.users_events]
        output['messages'] = [message.to_dict() for message in self.messages]
        return output


class Message(db.Model):
    '''
    Message har columner för id, text, user_id och event_id.

    to_dict() metod
    '''
    __tablename__ = 'Message'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250))
    author = db.Column(db.Integer, db.ForeignKey('User.name'))
    event = db.Column(db.Integer, db.ForeignKey('Event.name'))

    def to_dict(self):
        output = {}
        output["id"] = self.id
        output["text"] = self.text
        output['author'] = self.author
        output['event'] = self.event
        return output


class JWT_blocklist(db.Model):
    '''
    JWT_blocklist har columner för id och revoked_token.

    revoked_token är en sträng som är en JWT token som har blivit utloggad.
    '''
    __tablename__ = "JWT_blocklist"
    id = db.Column(db.Integer, primary_key=True)
    revoked_token = db.Column("token", db.String(700), unique=True)
