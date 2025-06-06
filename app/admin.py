from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import current_user, login_required, login_user
from .models import User
from app import db, bcrypt

#def create_admin_user():
#    if not User.query.filter_by(username="admin").first():
#        hashed_pw = bcrypt.generate_password_hash("admin").decode("utf-8")
#        admin = User(
#            username="admin",
#            email="admin@myapp.com",  
#            role="admin"              # use role, not is_admin
#        )
#        admin.set_password("admin")
#        db.session.add(admin)
#        db.session.commit()
def create_admin_user():
    with current_app.app_context():
        admin_user = User.query.filter_by(email='admin@myapp.com').first()
        if not admin_user:
            from werkzeug.security import generate_password_hash
            new_admin = User(
                username='admin',
                email='admin@myapp.com',
                password_hash=generate_password_hash('your_admin_password'),
                role='admin'
            )
            db.session.add(new_admin)
            db.session.commit()

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
def admin_panel():
    if current_user.role != "admin":
        flash("Access denied.")
        return redirect(url_for('main.index'))
    users = User.query.all()
    return render_template('admin.html', users=users)

@admin_bp.route('/impersonate/<int:user_id>')
@login_required
def impersonate(user_id):
    if current_user.role != "admin":
        flash("Access denied.")
        return redirect(url_for("main.index"))
    user = User.query.get_or_404(user_id)
    login_user(user)
    flash(f"Now impersonating {user.username}")
    return redirect(url_for("main.index"))
