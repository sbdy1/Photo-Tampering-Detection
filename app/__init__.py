from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app():
    app = Flask(__name__, static_folder="static")
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_default")

    app.config.from_object('config')

    # Use DATABASE_URL if provided, otherwise fallback to config.py value
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url

    app.config['SECRET_KEY'] = 'thisisasecretkey'
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024  # 60MB

    print("FINAL SQLALCHEMY_DATABASE_URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id)) # type : ignore

    from .auth import auth_bp
    from .routes import main_bp
    from .admin import admin_bp, create_admin_user
    from .upload import bp as upload_bp

    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()
        create_admin_user()
    return app
