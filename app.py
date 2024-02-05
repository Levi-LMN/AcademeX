from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo
from flask import request
from flask import Flask, render_template, flash, redirect, url_for

from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'levi5769!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    classes_taught = db.relationship('Class', backref='teacher', lazy=True)
    children = db.relationship('Student', backref='parent', lazy=True)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(50), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    students = db.relationship('Student', backref='class_students', lazy=True)

    def edit_class(self, class_name, teacher_id):
        self.class_name = class_name
        self.teacher_id = teacher_id
        db.session.commit()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    admission_number = db.Column(db.String(20), unique=True, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Change to nullable=True
    grades = db.relationship('Grade', backref='student_grades', lazy=True)
    attendance = db.relationship('Attendance', backref='student_attendance', lazy=True)


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Boolean, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('Admin', 'Admin'), ('Teacher', 'Teacher'), ('Parent', 'Parent')], validators=[DataRequired()])
    submit = SubmitField('Register')

# Update the AddClassForm in your app.py file
class AddClassForm(FlaskForm):
    class_name = StringField('Class Name', validators=[DataRequired()])
    teacher_id = SelectField('Teacher', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Class')


# Update the AddStudentForm in your forms.py file
class AddStudentForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    admission_number = StringField('Admission Number', validators=[DataRequired()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Student')




class AdminUsersForm(FlaskForm):
    submit = SubmitField('Change Role')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'Teacher':
            return redirect(url_for('teacher_dashboard'))
        elif current_user.role == 'Parent':
            return redirect(url_for('parent_dashboard'))
    return render_template('index.html')


# Update the admin_dashboard route in your app.py file
@app.route('/admin_dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    users = User.query.all()
    form = AdminUsersForm()
    add_class_form = AddClassForm()  # Instantiate AddClassForm here
    classes = Class.query.all()

    return render_template('admin/admin_dashboard.html', users=users, form=form, add_class_form=add_class_form, classes=classes)


@app.route('/manage_user_roles', methods=['GET', 'POST'])
@login_required
def manage_user_roles():
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    users = User.query.all()
    form = AdminUsersForm()

    if request.method == 'POST' and form.validate_on_submit():
        for user in users:
            new_role = request.form.get(f'role_{user.id}')
            if new_role in ['Admin', 'Teacher', 'Parent']:
                user.role = new_role

        db.session.commit()
        flash('User roles changed successfully.', 'success')
        return redirect(url_for('manage_user_roles'))

    return render_template('admin/users.html', users=users, form=form)


@app.route('/delete_user/<int:user_id>', methods=['GET'])
@login_required
def delete_user(user_id):
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    user_to_delete = User.query.get(user_id)

    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('User deleted successfully.', 'success')

    return redirect(url_for('manage_user_roles'))

# Update the teacher_dashboard route in your app.py file
@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'Teacher':
        return abort(403)  # Forbidden

    # Assuming a teacher can be assigned to at most one class
    teacher_class = Class.query.filter_by(teacher_id=current_user.id).first()

    if not teacher_class:
        flash('You are not assigned to any class yet.', 'info')
        return render_template('teacher_dashboard.html', teacher_class=None, students=[], flash=flash)

    # Get the students for the teacher's class
    students = Student.query.filter_by(class_id=teacher_class.id).all()

    return render_template('teacher_dashboard.html', teacher_class=teacher_class, students=students, flash=flash)


@app.route('/parent_dashboard')
@login_required
def parent_dashboard():
    if current_user.role != 'Parent':
        return abort(403)  # Forbidden
    return render_template('parent_dashboard.html')




@app.route('/admin_change_role/<int:user_id>/<new_role>')
@login_required
def admin_change_role(user_id, new_role):
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden
    user = User.query.get(user_id)
    if user:
        user.role = new_role
        db.session.commit()
        flash(f'Role for {user.username} changed to {new_role}.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('admin_dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Assuming you have a User model with a 'username' and 'password' field
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')

            # Redirect to the appropriate dashboard based on the user's role
            if user.role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'Teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user.role == 'Parent':
                return redirect(url_for('parent_dashboard'))
        else:
            flash('Login failed. Please check your username and password.', 'danger')

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        role = form.role.data

        # Check if the username or email is already taken
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already taken. Please choose a different one.', 'danger')
        else:
            # Create a new user
            new_user = User(username=username, email=email, password=generate_password_hash(password), role=role)

            # Add the user to the database
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html', form=form)


# Update the add_class route in your app.py file
@app.route('/add_class', methods=['GET', 'POST'])
@login_required
def add_class():
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    form = AddClassForm()

    # Filter teachers who don't have classes
    teachers_without_classes = User.query.filter_by(role='Teacher').filter_by(classes_taught=None).all()
    form.teacher_id.choices = [(teacher.id, teacher.username) for teacher in teachers_without_classes]

    if not teachers_without_classes:
        flash('No teachers available. Please add teachers before creating a class.', 'danger')

    if form.validate_on_submit():
        class_name = form.class_name.data
        teacher_id = form.teacher_id.data

        # Check if the class name is already taken
        if Class.query.filter_by(class_name=class_name).first():
            flash('Class name already taken. Please choose a different one.', 'danger')
        else:
            # Create a new class
            new_class = Class(class_name=class_name, teacher_id=teacher_id)

            # Add the class to the database
            db.session.add(new_class)
            db.session.commit()

            flash('Class added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_class.html', add_class_form=form)



# ... (existing imports)

@app.route('/delete_class/<int:class_id>', methods=['GET'])
@login_required
def delete_class(class_id):
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    class_to_delete = Class.query.get(class_id)

    if class_to_delete:
        try:
            # Delete related students
            students_to_delete = Student.query.filter_by(class_id=class_id).all()
            for student in students_to_delete:
                db.session.delete(student)

            db.session.delete(class_to_delete)
            db.session.commit()
            flash('Class deleted successfully.', 'success')

        except IntegrityError:
            # Handle IntegrityError due to foreign key constraints
            db.session.rollback()
            flash('Error: There are related records in the database.', 'danger')

    return redirect(url_for('admin_dashboard'))


# Update the edit_class route in your app.py file
@app.route('/edit_class/<int:class_id>', methods=['GET', 'POST'])
@login_required
def edit_class(class_id):
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    class_to_edit = Class.query.get(class_id)
    form = AddClassForm(obj=class_to_edit)

    # Populate the teacher_id choices with all teachers
    form.teacher_id.choices = [(teacher.id, teacher.username) for teacher in User.query.filter_by(role='Teacher').all()]

    if class_to_edit and form.validate_on_submit():
        form.populate_obj(class_to_edit)
        db.session.commit()

        flash('Class details updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_class.html', add_class_form=form)


# ... existing code ...

# ... (existing imports)

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    form = AddStudentForm()

    # Populate the class choices in the form
    form.class_id.choices = [(c.id, c.class_name) for c in Class.query.all()]

    if form.validate_on_submit():
        # Create a new student with parent_id set to None
        new_student = Student(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            admission_number=form.admission_number.data,
            class_id=form.class_id.data,
            parent_id=None  # Set parent_id to None initially
        )

        # Add the student to the database
        db.session.add(new_student)
        db.session.commit()

        flash('Student added successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_student.html', title='Add Student', form=form)


# Add this route to your app.py file
@app.route('/view_all_students', methods=['GET'])
@login_required
def view_all_students():
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    students = Student.query.all()

    return render_template('admin/view_all_students.html', students=students)

# Add this route to your app.py file
@app.route('/view_student/<int:student_id>', methods=['GET'])
@login_required
def view_student(student_id):
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    student = Student.query.get(student_id)

    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/view_student.html', student=student)


@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    student = Student.query.get(student_id)

    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    form = AddStudentForm(obj=student)
    form.class_id.choices = [(c.id, c.class_name) for c in Class.query.all()]

    if form.validate_on_submit():
        form.populate_obj(student)
        db.session.commit()

        flash('Student details updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/edit_student.html', title='Edit Student', form=form, student=student)


@app.route('/delete_student/<int:student_id>', methods=['GET'])
@login_required
def delete_student(student_id):
    if current_user.role != 'Admin':
        return abort(403)  # Forbidden

    student_to_delete = Student.query.get(student_id)

    if student_to_delete:
        db.session.delete(student_to_delete)
        db.session.commit()
        flash('Student deleted successfully.', 'success')

    return redirect(url_for('admin_dashboard'))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
