from flask import Flask
from config import Config, Configtesting
from models import db, bcrypt
from routes import user_bp, event_bp, bp, jwt


def create_app(testing=False):
    if testing:
        config_class = Configtesting
    else:
        config_class = Config

    app = Flask(__name__)

    app.config.from_object(config_class)
    app.config.from_prefixed_env()
    
    app.register_blueprint(user_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(bp)


    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    


    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)