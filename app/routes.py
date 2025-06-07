from flask import Blueprint, render_template, session, flash, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=["GET"])
@login_required
def index():
    if current_user.is_authenticated:
        print("현재 로그인 사용자:", current_user.username)
    return render_template(
        "index.html",
        user=current_user,
        original_img=session.get("original_filename"),
        processed_imgs=session.get("processed_filenames", [])
    )
    
@main_bp.route('/clear', methods=["POST"])
@login_required
def clear_session():
    session.pop('original_filename', None)
    session.pop('processed_filenames', None)
    flash("Images cleared.")
    return redirect(url_for('main.index'))
