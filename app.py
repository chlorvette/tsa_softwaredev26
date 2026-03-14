from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, text
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

initial_course_data = [
    {
        'title': 'Algebra 1 Basics',
        'subject': 'Math',
        'description': 'This course covers the fundamentals of Algebra 1, including variables, equations, and functions.',
    },
    {
        'title': 'Introduction to Earth Science',
        'subject': 'Science',
        'description': "This course introduces the basic concepts of Earth Science, including geology, meteorology, and oceanography and explores the interactions between Earth's systems.",
    },
    {
        'title': 'Analyzing Poetry',
        'subject': 'English',
        'description': 'This course focuses on the techniques and methods used to analyze poetry. It will cover themes, structure, and literary devices.',
    },
    {
        'title': 'Exploring Biology',
        'subject': 'Science',
        'description': 'This course explores the fundamental concepts of biology and explores cell structure, genetics, and ecosystems.',
    },
    {
        'title': 'The American Revolution',
        'subject': 'History',
        'description': 'This course explores the causes and consequences of the American Revolution.',
    },
]

initial_lesson_titles = ['Lesson 1', 'Lesson 2', 'Lesson 3']


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    lessons = db.relationship('Lesson', backref='course', lazy=True, cascade='all, delete-orphan')


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    lesson_order = db.Column(db.Integer, nullable=False, default=1)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    dark_mode = db.Column(db.Boolean, nullable=False, default=False)
    font_size = db.Column(db.Integer, nullable=False, default=16)
    line_spacing = db.Column(db.Float, nullable=False, default=1.5)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def seed_course_data():
    if Course.query.count() > 0:
        return

    for course_data in initial_course_data:
        course = Course(
            title=course_data['title'],
            subject=course_data['subject'],
            description=course_data['description'],
        )
        db.session.add(course)
        db.session.flush()

        for index, lesson_title in enumerate(initial_lesson_titles, start=1):
            db.session.add(Lesson(title=lesson_title, lesson_order=index, course_id=course.id))

    db.session.commit()


def initialize_database():
    db.create_all()
    ensure_user_preference_columns()
    seed_course_data()


def ensure_user_preference_columns():
    inspector = inspect(db.engine)
    existing_columns = {column['name'] for column in inspector.get_columns('user')}
    migrations = []

    if 'dark_mode' not in existing_columns:
        migrations.append('ALTER TABLE user ADD COLUMN dark_mode BOOLEAN NOT NULL DEFAULT 0')
    if 'font_size' not in existing_columns:
        migrations.append('ALTER TABLE user ADD COLUMN font_size INTEGER NOT NULL DEFAULT 16')
    if 'line_spacing' not in existing_columns:
        migrations.append('ALTER TABLE user ADD COLUMN line_spacing FLOAT NOT NULL DEFAULT 1.5')

    if not migrations:
        return

    with db.engine.begin() as connection:
        for migration in migrations:
            connection.execute(text(migration))

@app.before_request
def init_db():
    if app.config.get('DB_INITIALIZED'):
        return

    initialize_database()
    app.config['DB_INITIALIZED'] = True


@app.context_processor
def inject_courses():
    courses = Course.query.order_by(Course.id).all()
    return {'courses': courses}

@app.route("/")
def home():
    return render_template("home.html", title="Home", homeActive="active", loggedIn=current_user.is_authenticated)

@app.route("/help")
def help():
    return render_template("help.html", title="Help", helpActive="active", loggedIn=current_user.is_authenticated)

@app.route("/settings")
def settings():
    return render_template("settings.html", title="Settings", settingsActive="active", loggedIn=current_user.is_authenticated)


@app.route('/api/preferences', methods=['GET'])
@login_required
def get_preferences():
    return jsonify({
        'darkMode': bool(current_user.dark_mode),
        'fontSize': int(current_user.font_size),
        'lineSpacing': float(current_user.line_spacing),
    })


@app.route('/api/preferences', methods=['POST'])
@login_required
def save_preferences():
    data = request.get_json(silent=True) or {}

    dark_mode = bool(data.get('darkMode', current_user.dark_mode))

    try:
        font_size = int(data.get('fontSize', current_user.font_size))
    except (TypeError, ValueError):
        font_size = current_user.font_size

    try:
        line_spacing = float(data.get('lineSpacing', current_user.line_spacing))
    except (TypeError, ValueError):
        line_spacing = current_user.line_spacing

    font_size = max(12, min(40, font_size))
    line_spacing = max(1.0, min(4.0, line_spacing))

    current_user.dark_mode = dark_mode
    current_user.font_size = font_size
    current_user.line_spacing = line_spacing
    db.session.commit()

    return jsonify({'success': True})

@app.route("/my-courses")
def my_courses():
    return render_template("my-courses.html", title="My Courses", myCoursesActive="active", loggedIn=current_user.is_authenticated)

@app.route("/course/<int:course_id>/")
def course_detail(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        return "Course not found", 404

    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.lesson_order).all()

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
def logout():
    complete_logout_url = url_for('complete_logout')
    return f"""
<!DOCTYPE html>
<html>
<head><title>Logging out...</title></head>
<body>
<script>
    localStorage.removeItem('darkMode');
    localStorage.removeItem('fontSize');
    localStorage.removeItem('lineSpacing');
    window.location.replace('{complete_logout_url}');
</script>
</body>
</html>
"""


@app.route("/logout/complete")
def complete_logout():
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
    user = db.session.get(User, user_id)
    if user:
        db.session.delete(user)
    db.session.commit()
    return redirect(url_for('logout'))

if __name__ == '__main__':
    with app.app_context():
        initialize_database()
    app.run(debug=True)