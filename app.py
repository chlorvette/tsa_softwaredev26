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
        'title': 'Intro to Earth Science',
        'subject': 'Science',
        'description': "This course introduces the basic concepts of Earth Science, including geology and oceanography by exploring interactions between Earth's systems.",
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

initial_achievement_data = [
    {
        "name": "Finished First Course",
        "description": "Completed your first course!",
        "image_url": "images/awards/first_course.png"
    },
    {
        "name": "First Dark Mode",
        "description": "Used dark mode for the first time!",
        "image_url": "images/awards/first_dark_mode.png"
    },
    {
        "name": "First Font Size Change",
        "description": "Changed font size for the first time!",
        "image_url": "images/awards/first_font_size.png"
    },
    {
        "name": "First Line Spacing Change",
        "description": "Changed line spacing for the first time!",
        "image_url": "images/awards/first_line_spacing.png"
    }
]


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
    
# For achievements and awards tracking
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(255))

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned = db.Column(db.Boolean, default=False)

# For tracking course and lesson progress
class LessonProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)

class CourseProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)

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

def seed_achievement_data():
    if Achievement.query.count() > 0:
        return

    for achievement_data in initial_achievement_data:
        achievement = Achievement(
            name=achievement_data["name"],
            description=achievement_data["description"],
            image_url=achievement_data["image_url"]
        )
        db.session.add(achievement)

    db.session.commit()


def initialize_database():
    db.create_all()
    ensure_user_preference_columns()
    seed_course_data()
    seed_achievement_data()


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

@app.route("/awards")
@login_required
def awards():
    achievements = db.session.query(
        Achievement.id,  # explicitly select id
        Achievement.name,
        Achievement.description,  # explicitly select description
        Achievement.image_url,
        UserAchievement.earned
    ).outerjoin(
        UserAchievement, 
        (UserAchievement.achievement_id == Achievement.id) & (UserAchievement.user_id == current_user.id)
    ).all()

    achievements_list = [
        {"name": a.name, "description": a.description, "image_url": a.image_url, "earned": bool(a.earned)}
        for a in achievements
    ]
    return render_template("awards.html", achievements=achievements_list, loggedIn=current_user.is_authenticated, awardsActive="active", title="Awards")

@app.route('/api/preferences', methods=['GET'])
@login_required
def get_preferences():
    return jsonify({
        'darkMode': bool(current_user.dark_mode),
        'fontSize': int(current_user.font_size),
        'lineSpacing': float(current_user.line_spacing),
    })

@app.route("/complete-course/<int:course_id>", methods=["POST"])
@login_required
def complete_course(course_id):

    progress = CourseProgress.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()

    if not progress:
        progress = CourseProgress(
            user_id=current_user.id,
            course_id=course_id,
            completed=True
        )
        db.session.add(progress)
    else:
        progress.completed = True

    achievement = Achievement.query.filter_by(name="Finished First Course").first()

    if achievement:
        existing = UserAchievement.query.filter_by(
            user_id=current_user.id,
            achievement_id=achievement.id
        ).first()

        if not existing:
            new_award = UserAchievement(
                user_id=current_user.id,
                achievement_id=achievement.id,
                earned=True
            )
            db.session.add(new_award)

    db.session.commit()

    return redirect(url_for("course_detail", course_id=course_id))

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

    # For "First Dark Mode" achievement
    if not current_user.dark_mode and dark_mode:
        achievement = Achievement.query.filter_by(name="First Dark Mode").first()
        if achievement:
            existing = UserAchievement.query.filter_by(
                user_id=current_user.id,
                achievement_id=achievement.id
            ).first()

        if not existing:
            new_award = UserAchievement(
                user_id=current_user.id,
                achievement_id=achievement.id,
                earned=True
            )
            db.session.add(new_award)
            db.session.commit()

    # For "First Font Size Change" achievement
    if current_user.font_size != font_size:
        achievement = Achievement.query.filter_by(name="First Font Size Change").first()
        if achievement:
            existing = UserAchievement.query.filter_by(
                user_id=current_user.id,
                achievement_id=achievement.id
            ).first()

        if not existing:
            new_award = UserAchievement(
                user_id=current_user.id,
                achievement_id=achievement.id,
                earned=True
            )
            db.session.add(new_award)
            db.session.commit()

    # For "First Line Spacing Change" achievement
    if current_user.line_spacing != line_spacing:
        achievement = Achievement.query.filter_by(name="First Line Spacing Change").first()
        if achievement:
            existing = UserAchievement.query.filter_by(
                user_id=current_user.id,
                achievement_id=achievement.id
            ).first()

        if not existing:
            new_award = UserAchievement(
                user_id=current_user.id,
                achievement_id=achievement.id,
                earned=True
            )
            db.session.add(new_award)
            db.session.commit()

    current_user.dark_mode = dark_mode
    current_user.font_size = font_size
    current_user.line_spacing = line_spacing
    db.session.commit()

    return jsonify({'success': True})

@app.route("/my-courses")
def my_courses():
    courses = Course.query.all()

    if current_user.is_authenticated:
        completed_courses = {
            cp.course_id for cp in CourseProgress.query.filter_by(
                user_id=current_user.id,
                completed=True
            ).all()
        }
    else:
        completed_courses = set()

    return render_template(
        "my-courses.html",
        courses=courses,
        completed_courses=completed_courses,
        loggedIn=current_user.is_authenticated
    )
@app.route("/course/<int:course_id>/")
def course_detail(course_id):
    course = db.session.get(Course, course_id)
    lessons = Lesson.query.filter_by(course_id=course.id)\
        .order_by(Lesson.lesson_order).all()

    progress_percent = 0

    if current_user.is_authenticated:
        completed_lessons = LessonProgress.query.filter_by(
            user_id=current_user.id,
            completed=True
        ).join(Lesson).filter(Lesson.course_id == course.id).count()

        total_lessons = len(lessons)

        if total_lessons > 0:
            progress_percent = int((completed_lessons / total_lessons) * 100)

        if CourseProgress.query.filter_by(user_id=current_user.id, course_id=course.id, completed=True).first():
            progress_percent = 100

    return render_template(
        "course-detail.html",
        course=course,
        lessons=lessons,
        progress_percent=progress_percent,
        loggedIn=current_user.is_authenticated
    )
@app.route("/complete-lesson/<int:lesson_id>", methods=["POST"])
@login_required
def complete_lesson(lesson_id):
    progress = LessonProgress.query.filter_by(
        user_id=current_user.id,
        lesson_id=lesson_id
    ).first()

    if not progress:
        progress = LessonProgress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            completed=True
        )
        db.session.add(progress)
    else:
        progress.completed = True

    db.session.commit()

    lesson = db.session.get(Lesson, lesson_id)

    return redirect(url_for("course_detail", course_id=lesson.course_id))

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