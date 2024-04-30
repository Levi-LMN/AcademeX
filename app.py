from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import request, redirect, url_for, flash


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
    classes = db.relationship("Class", backref="teacher_association", lazy=True)


class Parent(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('parent', uselist=False))
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)  # Added foreign key relationship
    classes = db.relationship('Class', backref='parent', lazy=True)


class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admission_number = db.Column(db.String(20), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)
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

# Define the homepage route
@app.route('/')
def home():
    return render_template('index.html')


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


@app.route('/parent_dashboard')
@login_required  # Assuming parent needs to be logged in to access the dashboard
def parent_dashboard():
    return render_template('parent_dashboard.html')



from flask import redirect, url_for

@app.route('/send_association_request', methods=['POST'])
@login_required
def send_association_request():
    if request.method == 'POST':
        # Get the current parent
        parent = Parent.query.filter_by(user_id=current_user.id).first()

        # Get the admission number submitted in the form
        student_admission_number = request.form['student_admission_number']

        # Find the student with the given admission number
        student = Student.query.filter_by(admission_number=student_admission_number).first()

        if student:
            # Check if the association request already exists
            existing_request = AssociationRequest.query.filter_by(parent_id=parent.id, student_id=student.id).first()
            if existing_request:
                flash('Association request already sent for this student.', 'info')
            else:
                # Create a new association request
                new_request = AssociationRequest(parent_id=parent.id, student_id=student.id)
                db.session.add(new_request)
                db.session.commit()
                # Update the student's parent_id in the database
                student.parent_id = parent.id
                db.session.commit()
                flash('Association request sent successfully.', 'success')
                # Redirect to the parent dashboard
                return redirect(url_for('parent_dashboard'))
        else:
            flash('Student not found with the provided admission number.', 'error')

        return redirect(url_for('parent_dashboard'))



@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        admission_number = request.form['admission_number']
        student_name = request.form['student_name']
        class_id = request.form['class_id']

        # Create a new student object and add it to the database
        new_student = Student(admission_number=admission_number, name=student_name, class_id=class_id)
        db.session.add(new_student)
        db.session.commit()

        flash('Student added successfully!', 'success')
        return redirect(url_for('add_student'))  # Redirect to the same page to clear the form

    # Query all classes to populate the dropdown menu
    classes = Class.query.all()

    return render_template('admin/add_student.html', classes=classes)

# Define the teacher dashboard route
@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    # Get the current teacher
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()

    # Get the classes taught by the teacher
    classes_taught = teacher.classes

    return render_template('teacher_dashboard.html', classes_taught=classes_taught)

# Import necessary modules
from flask import render_template

# Define route for teacher to view students in their class
@app.route('/view_students')
@login_required
def view_students():
    # Check if the current user is a teacher
    if current_user.role != 'Teacher':
        flash('You are not authorized to view this page.', 'error')
        return redirect(url_for('dashboard'))

    # Get the current teacher
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()

    # Get the classes taught by the teacher
    classes_taught = teacher.classes

    # Check if the teacher is assigned to any class
    if not classes_taught:
        flash('You are not assigned to any class.', 'info')
        return redirect(url_for('dashboard'))

    # Get the first class taught by the teacher (assuming a teacher can only teach one class)
    teacher_class = classes_taught[0]

    # Get the students in the class
    students_in_class = teacher_class.students

    return render_template('teacher/view_students.html', students=students_in_class, teacher_class=teacher_class)


# Define route for teacher to view and manage association requests
@app.route('/view_and_manage_association_requests', methods=['GET', 'POST'])
@login_required
def view_and_manage_association_requests():
    # Check if the current user is a teacher
    if current_user.role != 'Teacher':
        flash('You are not authorized to view this page.', 'error')
        return redirect(url_for('dashboard'))

    # Get the current teacher
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()

    # Get the classes taught by the teacher
    classes_taught = teacher.classes

    # Check if the teacher is assigned to any class
    if not classes_taught:
        flash('You are not assigned to any class.', 'info')
        return redirect(url_for('dashboard'))

    # Initialize an empty list to store association requests
    association_requests = []

    # Iterate over the classes taught by the teacher
    for class_taught in classes_taught:
        # Get the students in the class
        students_in_class = class_taught.students

        # Get association requests related to the students in the class
        requests = AssociationRequest.query.filter(
            AssociationRequest.student_id.in_(student.id for student in students_in_class),
            AssociationRequest.status == 'pending'
        ).all()
        association_requests.extend(requests)

    # Handle form submission
    if request.method == 'POST':
        request_id = request.form.get('request_id')
        action = request.form.get('action')

        # Find the association request
        association_request = AssociationRequest.query.get(request_id)

        if association_request:
            # Update the status based on the action
            if action == 'accept':
                association_request.status = 'accepted'
                flash('Association request accepted successfully.', 'success')
            elif action == 'decline':
                association_request.status = 'declined'
                flash('Association request declined successfully.', 'success')

            db.session.commit()

            # Redirect to the same page to refresh the list of requests
            return redirect(url_for('view_and_manage_association_requests'))

    return render_template('teacher/view_association_requests.html', association_requests=association_requests)

from flask import render_template, redirect, url_for

# Define route for displaying child details
@app.route('/child_details/<int:student_id>')
@login_required
def child_details(student_id):
    # Query the student based on the provided student_id
    student = Student.query.get(student_id)

    # Check if the student exists and if the current parent is associated with the student
    if student and student.parent_id == current_user.parent.id:
        # Pass the student object to the template for rendering
        return render_template('parent/child_details.html', student=student)
    else:
        flash('You are not authorized to view this child\'s details.', 'error')
        return redirect(url_for('parent_dashboard'))




# Define route to view all students
@app.route('/view_all_students')
@login_required
def view_all_students():
    # Query all students with their associated classes
    students_with_class = db.session.query(Student, Class).join(Class).all()
    return render_template('admin/view_all_students.html', students_with_class=students_with_class)


from flask import render_template


# Define route to view students of a class
@app.route('/view_class_students/<int:class_id>')
@login_required
def view_class_students(class_id):
    # Query the class object
    class_ = Class.query.get(class_id)

    if class_ is None:
        # Handle case when class is not found
        flash('Class not found.', 'error')
        return redirect(url_for('manage_classes'))

    # Get the students of the class
    students = class_.students

    return render_template('admin/view_class_students.html', class_=class_, students=students)


# Define route to view details of a student
@app.route('/view_student_details/<int:student_id>')
@login_required
def view_student_details(student_id):
    # Query the student object
    student = Student.query.get(student_id)

    if student is None:
        # Handle case when student is not found
        flash('Student not found.', 'error')
        return redirect(url_for('view_all_students'))

    # Pass the student object to the template
    return render_template('admin/view_student.html', student=student)

# Define route for teacher to add students' grades
@app.route('/add_grades', methods=['GET', 'POST'])
@login_required
def add_grades():
    # Check if the current user is a teacher
    if current_user.role != 'Teacher':
        flash('You are not authorized to access this page.', 'error')
        return redirect(url_for('dashboard'))

    # Handle form submission
    if request.method == 'POST':
        # Get form data
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')
        grade = request.form.get('grade')

        # Validate form data (you can add more validation if needed)

        # Create a new Grade object and add it to the database
        new_grade = Grade(student_id=student_id, course_id=course_id, grade=grade)
        db.session.add(new_grade)
        db.session.commit()

        flash('Grade added successfully!', 'success')

        # Redirect to the same page to clear the form
        return redirect(url_for('add_grades'))

    # Query classes taught by the teacher
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    teacher_class = teacher.classes[0]  # Assuming a teacher teaches only one class

    # Query students enrolled in the teacher's class
    students = teacher_class.students

    # Query courses taught in the teacher's class
    courses_taught = teacher_class.courses

    return render_template('teacher/add_grades.html', courses=courses_taught, students=students)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
