from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from datetime import timedelta
import os

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

db = SQLAlchemy()  # Make sure db is instantiated here if not imported

def create_app():
    app = Flask(__name__, static_folder="static")

    # Load base config from config.py
    app.config.from_object('config')

    raw_uri = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
    if raw_uri.startswith("postgres://"):  # old Heroku style
        raw_uri = raw_uri.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = raw_uri
    # Override SECRET_KEY from environment or use default
    app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", app.config.get('SECRET_KEY', 'dev_secret'))
    
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=10)
    # Upload settings
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif", "heic", "heif"}
    app.config["ELA_QUALITY"] = 90 # Quality for ELA re-compression

    app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024  # 60MB max upload size

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))  # type: ignore

    # Import and register blueprints
    from .auth import auth_bp
    from .routes import main_bp
    from .admin import admin_bp, create_admin_user
    from .upload import bp as upload_bp

    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(upload_bp)

        # Create tables and ensure admin user exists
    #print("🟢 Running db.create_all() in app context")
    #with app.app_context():
    #    db.create_all()
    #    create_admin_user()

    return app
