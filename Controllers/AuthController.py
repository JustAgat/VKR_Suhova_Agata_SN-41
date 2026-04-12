from application import app, db
from flask import request, render_template, redirect, url_for, session, flash
from flask_restful import Resource
from Models.User import User
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


class AuthController(Resource):

    @staticmethod
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            if not email or not password:
                flash('Заполните все поля', 'error')
                return render_template('login.html')

            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['user_id'] = str(user.id)
                session['user_name'] = user.name
                return redirect(url_for('dashboard'))
            else:
                flash('Неверный email или пароль', 'error')
                return render_template('login.html')

        return render_template('login.html')

    @staticmethod
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')

            if not name or not email or not password:
                flash('Заполните все поля', 'error')
                return render_template('register.html')

            if password != password_confirm:
                flash('Пароли не совпадают', 'error')
                return render_template('register.html')

            if len(password) < 6:
                flash('Пароль должен быть не менее 6 символов', 'error')
                return render_template('register.html')

            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('Пользователь с таким email уже существует', 'error')
                return render_template('register.html')

            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            session['user_id'] = str(user.id)
            session['user_name'] = user.name
            return redirect(url_for('dashboard'))

        return render_template('register.html')

    @staticmethod
    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @staticmethod
    @app.route('/dashboard')
    @login_required
    def dashboard():
        user = User.query.get(session['user_id'])
        return render_template('dashboard.html', user=user)
