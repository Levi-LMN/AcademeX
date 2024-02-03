from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo
from flask import request

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

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.DateTime, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    grades = db.relationship('Grade', backref='student_grades', lazy=True)

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


@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
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
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/admin_dashboard.html', users=users, form=form)


@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'Teacher':
        return abort(403)  # Forbidden
    return render_template('teacher_dashboard.html')

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
