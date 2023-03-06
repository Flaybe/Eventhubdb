from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager, get_jwt, create_access_token
from models import Event, User, Message, JWT_blocklist, db, bcrypt


event_bp = Blueprint('eventbp', __name__, url_prefix='/event')

user_bp = Blueprint('sad', __name__, url_prefix='/user')

bp = Blueprint('standard', __name__)

jwt = JWTManager()


@bp.route('/hello')
def hello_world():
    return 'Hello, World!'


@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(name=data['name']).one_or_none()

    if user is None:
        return jsonify({'response': 'Wrong username or password'}), 401

    elif not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'response': 'Wrong username or password'}), 401

    else:
        token = create_access_token(identity=user.name, expires_delta=None)
        return jsonify(access_token=token), 200


@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    user = User.query.filter_by(name=data['name']).one_or_none()
    if user is not None:
        return jsonify({'response': 'Username already exists'}), 400

    new_user = User(name=data['name'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'response': 'User created'}), 200


@user_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    revoked = JWT_blocklist(revoked_token=jti)
    db.session.add(revoked)
    db.session.commit()
    return jsonify({'response': 'Logout successful'}), 200


@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    is_revoked = JWT_blocklist.query.filter_by(revoked_token=jti).first()
    if is_revoked is None:
        return False
    return True


@user_bp.route('/<string:name>', methods=['GET'])
@jwt_required()
def get_user(name):
    user = User.query.filter_by(name=name).one_or_none()
    if user is None:
        return jsonify({'response': 'User not found'}), 404
    return jsonify(user.to_dict()), 200


@event_bp.route('/create', methods=['POST'])
@jwt_required()
def create_event():
    data = request.get_json()
    user = User.query.filter_by(name=get_jwt_identity()).one_or_none()
    if user is None:
        return jsonify({'response': 'User not found'}), 404
    new_event = Event(
        name=data['name'], description=data['description'], creator=user.name)
    db.session.add(new_event)
    db.session.commit()
    return jsonify({'response': 'Event created'}), 200


@event_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_events():
    events = Event.query.all()
    return jsonify([event.to_dict() for event in events]), 200


@event_bp.route('/<string:name>', methods=['GET'])
@jwt_required()
def get_event(name):
    event = Event.query.filter_by(name=name).one_or_none()
    if event is None:
        return jsonify({'response': 'Event not found'}), 404
    return jsonify(event.to_dict()), 200


@event_bp.route('/join/<string:name>', methods=['POST'])
@jwt_required()
def join_event(name):
    user = User.query.filter_by(name=get_jwt_identity()).one_or_none()
    event = Event.query.filter_by(name=name).one_or_none()
    if user is None:
        return jsonify({'response': 'User not found'}), 404
    if event is None:
        return jsonify({'response': 'Event not found'}), 404

    if user in event.users_in_event:
        return jsonify({'response': 'User already in event'}), 202

    event.users_in_event.append(user)
    db.session.commit()
    return jsonify({'response': 'Joined event'}), 200


@event_bp.route('/leave/<string:name>', methods=['POST'])
@jwt_required()
def leave_event(name):
    user = User.query.filter_by(name=get_jwt_identity()).one_or_none()
    event = Event.query.filter_by(name=name).one_or_none()

    if user is None:
        return jsonify({'response': 'User not found'}), 404

    if event is None:
        return jsonify({'response': 'Event not found'}), 404

    if user not in event.users_in_event:
        return jsonify({'response': 'User not in event'}), 404

    event.users_in_event.remove(user)
    db.session.commit()

    return jsonify({'response': 'Left event'}), 200


@event_bp.route('/send/<string:name>', methods=['POST'])
@jwt_required()
def send_message(name):
    data = request.get_json()
    user = User.query.filter_by(name=get_jwt_identity()).one_or_none()
    event = Event.query.filter_by(name=name).one_or_none()

    if user is None:
        return jsonify({'response': 'User not found'}), 404

    if event is None:
        return jsonify({'response': 'Event not found'}), 404

    new_message = Message(
        text=data['text'], author=user.name, event=event.name)

    if user.name not in event.users_in_event:
        event.users_in_event.append(user)
        db.session.add(event)

    db.session.add(new_message)
    db.session.commit()

    return jsonify({'response': 'Message sent'}), 200


@event_bp.route('/messages/<string:name>', methods=['GET'])
@jwt_required()
def get_messages(name):
    event = Event.query.filter_by(name=name).one_or_none()

    if event is None:
        return jsonify({'response', 'Event not found'}), 404

    messages = Message.query.all()
    return jsonify([message.to_dict() for message in messages]), 200


@event_bp.route('/message/<string:name>/<int:messageid>', methods=['GET'])
@jwt_required()
def get_message(name, messageid):
    event = Event.query.filter_by(name=name).one_or_none()
    message = Message.query.filter_by(id=messageid).one_or_none()

    if event is None:
        return jsonify({'response', 'Event not found'}), 404

    if message is None:
        return jsonify({'response', 'Message not found'}), 404
    print(message.to_dict())
    return jsonify(message.to_dict()), 200
