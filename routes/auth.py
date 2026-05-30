from functools import wraps

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from services.users import authenticate

auth_bp = Blueprint('auth', __name__)


def login_required(view):
    """Redirect HTML routes to /login; return 401 JSON for /api/*."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    """Gate a view to the 'admin' user. 403 (JSON for /api/*) otherwise.

    No role system exists — admin is simply username == 'admin'.
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
            return redirect(url_for('auth.login'))
        if session.get('username') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': 'Admin only'}), 403
            return abort(403)
        return view(*args, **kwargs)
    return wrapper


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if authenticate(username, password):
            session.permanent = True
            session['username'] = username
            session.pop('active_qc_file', None)
            session['patient_index'] = 0
            session['phase'] = 'ED'
            return redirect(url_for('pages.index'))
        return render_template('login.html', error='Incorrect username or password')
    return render_template('login.html', error=None)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
