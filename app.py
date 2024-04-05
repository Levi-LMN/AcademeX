from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Set your secret key for session security
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Define User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # Admin, Teacher, Parent

# Define other models
class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('admin', uselist=False))

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    teacher = relationship("Teacher", back_populates="classes")

class Teacher(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject_taught = db.Column(db.String(50), nullable=True)
    user = db.relationship('User', backref=db.backref('teacher', uselist=False))
    classes = relationship("Class", back_populates="teacher")

class Parent(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('parent', uselist=False))
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)  # Added foreign key relationship
    classes = db.relationship('Class', backref='parent', lazy=True)

class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_number = db.Column(db.String(20), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    parent = db.relationship('Parent', backref=db.backref('students', lazy=True))
    class_ = db.relationship('Class', backref=db.backref('students', lazy=True))


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    student = db.relationship('Student', backref=db.backref('enrollments', lazy=True))
    course = db.relationship('Course', backref=db.backref('enrollments', lazy=True))

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollment.id'), nullable=False)
    grade = db.Column(db.Float, nullable=False)
    enrollment = db.relationship('Enrollment', backref=db.backref('grades', lazy=True))

class AssociationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'accepted', 'declined'
    student = db.relationship('Student', backref=db.backref('association_requests', lazy=True))
    parent = db.relationship('Parent', backref=db.backref('association_requests', lazy=True))

# User loader function required by Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Define the registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please choose a different email.', 'error')
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Create a new user
        new_user = User(first_name=first_name, last_name=last_name, email=email, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')

        # Create corresponding entry in the respective tables based on user role
        if role == 'Admin':
            new_admin = Admin(user_id=new_user.id)
            db.session.add(new_admin)
            db.session.commit()
        elif role == 'Teacher':
            new_teacher = Teacher(user_id=new_user.id)
            db.session.add(new_teacher)
            db.session.commit()
        elif role == 'Parent':
            new_parent = Parent(user_id=new_user.id)
            db.session.add(new_parent)
            db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)  # Log in the user
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid email or password. Please try again.', 'error')

    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()  # Log out the user
    return redirect(url_for('login'))

# Dashboard route
@app.route('/dashboard')
@login_required
def dashboard():
    # Render dashboard based on user role
    if current_user.role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'Teacher':
        return redirect(url_for('teacher_dashboard'))
    elif current_user.role == 'Parent':
        return redirect(url_for('parent_dashboard'))

# Define the admin dashboard route
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

# Define the route to manage users
@app.route('/manage_users')
def manage_users():
    users = User.query.all()
    return render_template('admin/manage_users.html', users=users)

# Define the route to manage courses
@app.route('/manage_courses')
def manage_courses():
    courses = Course.query.all()
    return render_template('admin/manage_courses.html', courses=courses)


# Define the route to add courses
@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if request.method == 'POST':
        name = request.form['name']

        # Create a new course
        new_course = Course(name=name)
        db.session.add(new_course)
        db.session.commit()

        flash('Course added successfully!', 'success')
        return redirect(url_for('manage_courses'))

    return render_template('admin/add_course.html')


# Define the route to add classes
# Define the route to add classes
@app.route('/add_class', methods=['GET', 'POST'])
def add_class():
    if request.method == 'POST':
        name = request.form['name']
        teacher_id = request.form['teacher']  # Get the selected teacher ID

        # Create a new class
        new_class = Class(name=name, teacher_id=teacher_id)
        db.session.add(new_class)
        db.session.commit()

        flash('Class added successfully!', 'success')
        return redirect(url_for('manage_classes'))

    # Fetch all teachers
    teachers = Teacher.query.all()

    print(teachers)  # Add this line to debug

    return render_template('admin/add_class.html', teachers=teachers)

# Define the teacher dashboard route
@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    return render_template('teacher_dashboard.html')


# Define route to render HTML page
@app.route('/manage_classes')
def manage_classes():
    # Query all classes
    classes = Class.query.all()

    # Create a dictionary to store teacher names by teacher id
    teacher_names = {}

    # Fetch all users and teachers
    users = User.query.all()
    teachers = Teacher.query.all()

    # Populate teacher names dictionary
    for teacher in teachers:
        teacher_names[teacher.user_id] = f"{teacher.user.first_name} {teacher.user.last_name}"

    print("Classes:", classes)  # Debug print
    print("Teacher Names:", teacher_names)  # Debug print

    # Pass classes and teacher names to the HTML template
    return render_template('admin/manage_classes.html', classes=classes, teacher_names=teacher_names)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
