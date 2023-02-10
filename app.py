from flask import Flask
from flask import request
from crypt import methods
from flask import jsonify
import uuid
from flask_sqlalchemy import SQLAlchemy
import os

def create_app():
    app = Flask(__name__)
    return app

app = create_app()
if not 'WEBSITE_HOSTNAME' in os.environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./test.db'

else:
    DATABASE_URI = 'postgresql+psycopg2://{dbuser}:{dbpass}@{dbhost}/{dbname}'.format(
        dbuser = os.environ['DBUSER'],
        dbpass = os.environ['DBPASS'],
        dbhost = os.environ['DBHOST'] + ".postgres.database.azure.com",
        dbname = os.environ['DBNAME'])
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    
db = SQLAlchemy(app)


read_by = db.Table('read_by',
    db.Column('user_id', db.Integer, db.ForeignKey('User.id')),
    db.Column('msg_id', db.Integer, db.ForeignKey('Message.id'))
    )

class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key = True)
    read_message = db.relationship("Message", secondary='read_by', back_populates="user_read_msg")
    
    
class Message(db.Model):
    __tablename__ = "Message"
    id = db.Column(db.Integer, primary_key = True)
    msg = db.Column(db.String(250))
    user_read_msg = db.relationship("User", secondary='read_by', back_populates="read_message")
    

    def to_dict(self):
        result = {}
        result['id'] = self.id
        result['message'] = self.msg
        idlist = [userid.id for userid in self.user_read_msg]
        result["read_by"] = idlist
    
        return result


@app.route("/messages", methods = ['POST'])
def save_message():
    data = request.json
    msgIn = data["message"]
    msg = Message(msg = msgIn)
    db.session.add(msg)
    db.session.commit()
    return jsonify({"response": "message saved"}), 200


@app.route("/messages", methods = ['GET'])
def get_all_msg():
    messages = Message.query.filter_by().all()
    temp_list = [msg.to_dict() for msg in messages]
    return jsonify(temp_list), 200


@app.route("/messages/<MessageID>", methods = ['GET'])
def get_msg(MessageID):
    message = Message.query.filter_by(id=MessageID).first()
    if message is not None:
        return jsonify(message.to_dict()), 200
    return  jsonify({'response' : "Message not found"}), 404 


@app.route("/messages/<MessageID>", methods = ['DELETE'])
def del_msg(MessageID):
    message = Message.query.filter_by(id=MessageID).first()
    if message is not None:
        db.session.delete(message)
        db.session.commit()
        return jsonify({"response" : "Message deleted"}), 200
    return  jsonify({'response' : "Message not found"}), 404 


@app.route("/messages/<MessageID>/read/<UserID>", methods = ["POST"])
def mark_as_read(MessageID, UserID):
    message = Message.query.filter_by(id=MessageID).first()
    if message is not None:
        user = User.query.filter_by(id=UserID).first()
        if user is None:
            user = User(id=UserID)
        message.user_read_msg.append(user)
        db.session.add(message)
        db.session.commit()
        return jsonify({"response" : "Message read"}), 200

    return  jsonify({'response' : "Message not found"}), 404 



@app.route("/messages/unread/<UserID>", methods = ["GET"])
def show_unread(UserID):
    output = []

    user = User.query.filter_by(id=UserID).first()

    if user is None:
        return jsonify({"response" : "User not found"}), 404
    read_msg = user.read_message
    all_msg = Message.query.filter_by().all()
    read_id = [id.id for id in read_msg]
    for message in all_msg:
        if message.id not in read_id:
            output.append(message.to_dict())
    return jsonify(output), 200


@app.route("/clearAll", methods = ["DELETE"])
def del_all():

    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        print("clear table %s" % table)
        db.session.execute(table.delete())
    db.session.commit()
    return "all deleted", 200


if __name__ == "__main__":
    app.debug = True
    db.init_app(app)
    app.run()
