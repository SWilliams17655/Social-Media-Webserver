import flask_login
import werkzeug.security
import os
import boto3
import string
import random
import logging
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
from flask_login import UserMixin, LoginManager, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.utils import secure_filename
from datetime import date
#
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
#
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "uploads"

load_dotenv()

app.config['SECRET_KEY'] = os.getenv('FLASK_KEY')

# Connects to the EquineSocial Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
db = SQLAlchemy()
db.init_app(app)

# Configures a flask login manager
login_manager = LoginManager()
login_manager.init_app(app)


# Creates a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# Creates the User table in the EquineSocial Database
class User(UserMixin, db.Model):
    email = db.Column(db.String(100), unique=True, nullable=False)
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=True)
    state = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    birthday = db.Column(db.String(50), nullable=True)
    page_image = db.Column(db.String(250), nullable=True)
    discipline = db.Column(db.String(250), nullable=True)
    about = db.Column(db.String(800), nullable=True)
    award = db.Column(db.String(800), nullable=True)

class Posts(UserMixin, db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    replies_to_post = db.Column(db.Integer)
    post_from = db.Column(db.Integer)
    post_to = db.Column(db.Integer)
    title = db.Column(db.String(50))
    date = db.Column(db.String(50))
    text = db.Column(db.String(500))

class Horses(UserMixin, db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    country = db.Column(db.String(50))
    birthday = db.Column(db.String(50))
    page_image = db.Column(db.String(50))
    discipline = db.Column(db.String(250), nullable=True)
    about = db.Column(db.String(800), nullable=True)
    award = db.Column(db.String(800), nullable=True)


# Creates the tables in the EquineSocial Database
with app.app_context():
    db.create_all()

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ****************************************************************************************'' \
# Functions to access pages.
# ****************************************************************************************'' \

@app.route('/')
def home_page():
    return render_template('index.html', message="", logged_in_user_file=None)

@app.route("/login", methods=["POST"])
def login_user():
    if request.method == "POST":
        email = request.form['input_email']
        password = request.form['input_password']
        result = db.session.execute(db.select(User).where(func.lower(User.email) == func.lower(email)))
        user = result.scalar()

        if user is None:
            return render_template('index.html', user_file=None, logged_in_user_file=None, message="Account does not exist, would you like to create an account?")

        if werkzeug.security.check_password_hash(user.password, password):
            flask_login.login_user(user)
            return redirect(f'/user_page/{user.id}')
        else:
            return render_template('index.html', user_file=None, logged_in_user_file=None, message="Incorrect email or password, please try again.")

@app.route('/user_page/<user_id>')
@login_required
def user_page(user_id):
    result = db.session.execute(db.select(User).where(User.id == user_id))
    user_file = result.scalar()
    result = db.session.execute(db.select(Posts).where(Posts.post_to == user_id).order_by(Posts.date.desc()))
    post_file = result.scalars()
    result = db.session.execute(db.select(Horses).where(Horses.owner_id == user_id))
    horse_file = result.scalars()
    return render_template('user_page.html', logged_in_user_file=flask_login.current_user, user_file=user_file, horse_file=horse_file, post_file=post_file)

@app.route('/horse_page/<horse_id>')
def horse_page(horse_id):
    result = db.session.execute(db.select(Horses).where(Horses.id == horse_id))
    horse_file = result.scalar()
    result = db.session.execute(db.select(User).where(User.id == horse_file.owner_id))
    owner_file = result.scalar()

    return render_template('horse_page.html', logged_in_user_file=flask_login.current_user, horse_file=horse_file, owner_file=owner_file, post_file=None)

@app.route('/my_connections/')
@login_required
def user_connections():
    result = db.session.execute(db.select(User).where(User.id == flask_login.current_user.id))
    user_file = result.scalar()
    connections_file = db.session.query(User).all()
    return render_template("connections_page.html", logged_in_user_file=flask_login.current_user, user_file=user_file, connections_file=connections_file)

@app.route("/logout")
@login_required
def logout_user():
    flask_login.logout_user()
    return redirect('/')
# ****************************************************************************************'' \
# Functions to update records.
# ****************************************************************************************'' \

@app.route('/user_page/upload_photo/', methods=["POST"])
@login_required
def upload_user_photo():
    if request.method == 'POST':
        user_id = flask_login.current_user.id
        file = request.files['file']
        f = secure_filename(file.filename)
        basedir = os.path.abspath(os.path.dirname(__file__))
        file.save(os.path.join(basedir, app.config['UPLOAD_FOLDER'], f))

        s3 = boto3.client('s3',
                          aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                          aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS')
                          )
        result = db.session.execute(db.select(User).where(User.id == user_id))
        user_file = result.scalar()
        try:
            s3.delete_object(
                        Bucket=os.getenv('BUCKET_NAME'),
                        Key=user_file.page_image,
            )
        except:
            print("Error: An error occurred while deleting the file. Most common cause is file did not exist.")
        finally:
            print("The deleting operation is complete.")
        random_string = get_random_string(12)
        upload_filename = f"{user_id}_user_{random_string}_{f}"
        print(f"Uploading new image: {upload_filename}")
        s3.upload_file(
                      Bucket=os.getenv('BUCKET_NAME'),
                      Filename=os.path.join(basedir, app.config['UPLOAD_FOLDER'], f),
                      Key=upload_filename
                  )
        db.session.execute(db.update(User)
                           .where(User.id == user_id)
                           .values(page_image=upload_filename)
                           )
        db.session.commit()
        os.remove(os.path.join(basedir, app.config['UPLOAD_FOLDER'], f))
        return redirect(f'/user_page/{user_id}')

@app.route('/horse_page/upload_photo/<horse_id>', methods=["POST"])
@login_required
def upload_horse_photo(horse_id):
    if request.method == 'POST':

        file = request.files['file']
        f = secure_filename(file.filename)
        basedir = os.path.abspath(os.path.dirname(__file__))
        file.save(os.path.join(basedir, app.config['UPLOAD_FOLDER'], f))

        s3 = boto3.client('s3',
                          aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                          aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS')
                          )
        result = db.session.execute(db.select(Horses).where(Horses.id == horse_id))
        horse_file = result.scalar()
        if flask_login.current_user.id == horse_file.owner_id:
            try:
                s3.delete_object(
                            Bucket=os.getenv('BUCKET_NAME'),
                            Key=horse_file.page_image,
                )
            except:
                print("Error: An error occurred while deleting the file. Most common cause is file did not exist.")
            finally:
                print("The deleting operation is complete.")
            random_string = get_random_string(12)
            upload_filename = f"{horse_id}_horse_{random_string}_{f}"
            print(f"Uploading new image: {upload_filename}")
            s3.upload_file(
                          Bucket=os.getenv('BUCKET_NAME'),
                          Filename=os.path.join(basedir, app.config['UPLOAD_FOLDER'], f),
                          Key=upload_filename
                      )
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(page_image=upload_filename)
                               )
            db.session.commit()
            os.remove(os.path.join(basedir, app.config['UPLOAD_FOLDER'], f))
        return redirect(f'/horse_page/{horse_id}')

@app.route("/user_page/update", methods=["POST"])
@login_required
def update_user():
    if request.method == "POST":
        first_name_value = request.form['input_first_name']
        if first_name_value != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(first_name=first_name_value)
                               )
        last_name_value = request.form['input_last_name']
        if last_name_value != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(last_name=last_name_value)
                               )
        city_value = request.form['input_city']
        if city_value != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(city=city_value)
                               )

        state_value = request.form['input_state']

        if state_value != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(state=state_value)
                               )

        country_value = request.form['input_country']
        if country_value != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(country=country_value)
                               )

        award = request.form['input_award']
        if award != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(award=award)
                               )
        about = request.form['input_about']
        if about != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(about=about)
                               )
        discipline = request.form['input_discipline']
        if discipline != "":
            db.session.execute(db.update(User)
                               .where(User.id == flask_login.current_user.id)
                               .values(discipline=discipline)
                               )
        db.session.commit()

        return redirect(f'/user_page/{flask_login.current_user.id}')

@app.route("/horse_page/update/<horse_id>", methods=["POST"])
@login_required
def update_horse(horse_id):
    if request.method == "POST":
        name_value = request.form['input_name']
        if name_value != "":
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(name=name_value)
                               )
        city_value = request.form['input_city']
        if city_value != "":
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(city=city_value)
                               )

        state_value = request.form['input_state']

        if state_value != "":
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(state=state_value)
                               )

        country_value = request.form['input_country']
        if country_value != "":
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(country=country_value)
                               )

        award = request.form['input_award']
        if award != "":
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(award=award)
                               )
        about = request.form['input_about']
        if about != "":
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(about=about)
                               )
        discipline = request.form['input_discipline']
        print(discipline)
        if discipline != "":
            db.session.execute(db.update(Horses)
                               .where(Horses.id == horse_id)
                               .values(discipline=discipline)
                               )

        db.session.commit()

        return redirect(f'/horse_page/{horse_id}')

@app.route("/update_user_password", methods=["POST"])
def update_user_password():
    if request.method == "POST":
        with app.app_context():
            app.logger.critical("Updating User Password")
            password_old = request.form['input_old_password']
            password_new = request.form['input_new_password']
            if werkzeug.security.check_password_hash(flask_login.current_user.password, password_old):
                db.session.execute(db.update(User)
                                   .where(User.id == flask_login.current_user.id)
                                   .values(password=werkzeug.security.generate_password_hash(password_new,
                                                                              method='pbkdf2:sha256', salt_length=16)))
                db.session.commit()


    return render_template('index.html', user_file=None, logged_in_user_file=None, message="Password updated, please login using your new password.")

# ****************************************************************************************'' \
# Functions to create records.
# ****************************************************************************************'' \
@app.route("/adduser", methods=["POST"])
def add_user():
    if request.method == "POST":
        with app.app_context():
            print(request.form)
            app.logger.critical("Adding user to RDS")
            new_user = User(email=request.form['input_email'],
                            password=werkzeug.security.generate_password_hash(request.form['input_password'],
                                                                              method='pbkdf2:sha256', salt_length=16),
                            first_name=request.form['input_first_name'],
                            last_name=request.form['input_last_name'],
                            )
            db.session.add(new_user)
            db.session.commit()
            return render_template('index.html', user_file=None, logged_in_user_file=None, message="New account created. Welcome to EquineSocial, please log in to set up your account.")

@app.route("/addhorse", methods=["POST"])
@login_required
def add_horse():
    if request.method == "POST":
        with app.app_context():
            new_horse = Horses(name=request.form['input_horse_name'],
                               owner_id=flask_login.current_user.id
                               )
            db.session.add(new_horse)
            db.session.commit()
    return redirect(f'/user_page/{flask_login.current_user.id}')

@app.route("/adduserpost/<user_id>/<submit_id>", methods=["POST"])
def add_user_post(user_id, submit_id):
    if request.method == "POST":
        with app.app_context():
            new_post = Posts(replies_to_post=0,
                             post_from=submit_id,
                             post_to=user_id,
                             title=request.form['input_title'],
                             date=date.today(),
                             text=request.form['input_post'])

            db.session.add(new_post)
            db.session.commit()
    return redirect(f'/user_page/{user_id}')

# ****************************************************************************************'' \
# Functions to delete records.
# ****************************************************************************************'' \
@app.route("/deleteuserpost/<post_id>/<user_id>")
def delete_user_post(post_id, user_id):
    print("in function")
    print("In request function")
    result = db.session.execute(db.select(Posts).where(Posts.id == post_id))
    post_file = result.scalar()
    print(post_file.text)
    Posts.query.filter(Posts.id == post_id).delete()
    db.session.commit()
    return redirect(f'/user_page/{user_id}')

if __name__ == '__main__':
    app.run(host='0.0.0.0')

