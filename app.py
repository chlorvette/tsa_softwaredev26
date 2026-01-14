from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def init_db():
    db.create_all()

@app.route("/")
def home():
    return render_template("home.html", title="Home", homeActive="active", loggedIn=current_user.is_authenticated)

@app.route("/help")
def help():
    return render_template("help.html", title="Help", helpActive="active", loggedIn=current_user.is_authenticated)

@app.route("/settings")
def settings():
    return render_template("settings.html", title="Settings", settingsActive="active", loggedIn=current_user.is_authenticated)
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid username or password', loginActive="active", loggedIn=current_user.is_authenticated)
    
    return render_template('login.html', loginActive="active", loggedIn=current_user.is_authenticated)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if password != password_confirm:
            return render_template('register.html', error='Passwords do not match', registerActive="active", loggedIn=current_user.is_authenticated)
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists', registerActive="active", loggedIn=current_user.is_authenticated)
        
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already exists', registerActive="active", loggedIn=current_user.is_authenticated)
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('home'))
    
    return render_template('register.html', registerActive="active", loggedIn=current_user.is_authenticated)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)