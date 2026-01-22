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

courses = [
    {'id': 1, 'title': 'Algebra 1 Basics', 'subject': 'Math', 'description': 'This course covers the fundamentals of Algebra 1, including variables, equations, and functions.'},
    {'id': 2, 'title': 'Introduction to Earth Science', 'subject': 'Science', 'description': 'This course introduces the basic concepts of Earth Science, including geology, meteorology, and oceanography and explores the interactions between Earth\'s systems.'},
    {'id': 3, 'title': 'Analyzing Poetry', 'subject': 'English', 'description': 'This course focuses on the techniques and methods used to analyze poetry. It will cover themes, structure, and literary devices.'},
    {'id': 4, 'title': 'Exploring Biology', 'subject': 'Science', 'description': 'This course explores the fundamental concepts of biology and explores cell structure, genetics, and ecosystems.'},
    {'id': 5, 'title': 'The American Revolution', 'subject': 'History', 'description': 'This course explores the causes and consequences of the American Revolution.'}
    ]

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

@app.route("/my-courses")
def my_courses():
    return render_template("my-courses.html", title="My Courses", myCoursesActive="active", loggedIn=current_user.is_authenticated)

@app.route("/course/<int:course_id>/")
def course_detail(course_id):
    course = next((c for c in courses if c['id'] == course_id), None)
    if not course:
        return "Course not found", 404
    
    lessons = [
        {'id': 1, 'title': 'Lesson 1'},
        {'id': 2, 'title': 'Lesson 2'},
        {'id': 3, 'title': 'Lesson 3'},
    ]
    
    return render_template("course-detail.html", course=course, lessons=lessons, loggedIn=current_user.is_authenticated)

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

@app.route("/change-username", methods=['POST'])
@login_required
def change_username():
    new_username = request.form.get('new_username')
    password = request.form.get('password')
    
    if not current_user.check_password(password):
        return render_template('settings.html', title="Settings", error='Incorrect password', settingsActive="active", loggedIn=current_user.is_authenticated), 401
    
    if User.query.filter_by(username=new_username).first():
        return render_template('settings.html', title="Settings", error='Username already taken', settingsActive="active", loggedIn=current_user.is_authenticated), 400
    
    current_user.username = new_username
    db.session.commit()
    return redirect(url_for('settings'))

@app.route("/change-password", methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        return render_template('settings.html', title="Settings", error='Incorrect current password'), 401
    
    if new_password != confirm_password:
        return render_template('settings.html', title="Settings", error='New passwords do not match'), 400
    
    current_user.set_password(new_password)
    db.session.commit()
    return redirect(url_for('settings'))

@app.route("/delete-account", methods=['POST'])
@login_required
def delete_account():
    password = request.form.get('password')
    
    if not current_user.check_password(password):
        return render_template('settings.html', title="Settings", error='Incorrect password'), 401
    
    user_id = current_user.id
    logout_user()
    db.session.delete(User.query.get(user_id))
    db.session.commit()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)