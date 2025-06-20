from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user,logout_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([username, email, password]):
            flash("All fields are required.")
            return redirect(url_for('auth.signup'))

        # Check if the user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered.')
            return redirect(url_for('auth.signup'))

        hashed_pw = generate_password_hash(password)
        # Determine role based on email
        role = 'admin' if username == 'admin' else 'user'

        new_user = User(username=username, email=email, role=role, password_hash=hashed_pw)    
        db.session.add(new_user)
        db.session.commit()
        
        flash(f"Account created successfully. Logged in as {role}")
        login_user(new_user)
        return render_template('base.html')

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        entered_password = request.form.get('password')  # <-- THIS is what was missing
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, entered_password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin.admin_panel'))
            else:
                return render_template('base.html')
        else:
            flash("Invalid credentials")
    return render_template('login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    session.clear()
    flash("Logged out.")
    return redirect(url_for('auth.login'))

@auth_bp.route('/delete_users', methods=['GET', 'POST'])
def delete_users():
    from app.models import User
    User.query.delete()
    db.session.commit()
    return "Deleted all users"
