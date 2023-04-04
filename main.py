import requests
import datetime as dt
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import urllib
from sqlalchemy.exc import IntegrityError
import atexit
from dotenv import load_dotenv
from flask_mail import Mail, Message
import os
from werkzeug.serving import is_running_from_reloader
from apscheduler.schedulers.background import BackgroundScheduler


load_dotenv()

my_email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
server_name = os.getenv("SERVER_NAME")
MY_EMAIL = os.environ.get("EMAIL", my_email)
PASSWORD = os.environ.get("PASSWORD", password)

app = Flask(__name__)

Secret_key = os.getenv("SECRET_KEY")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", Secret_key)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///user.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = MY_EMAIL
app.config['MAIL_PASSWORD'] = PASSWORD
app.config['MAIL_USE_TLS'] = True
app.config['SERVER_NAME'] = os.environ.get("SERVER_NAME", server_name)
app.config['PREFERRED_URL_SCHEME'] = os.environ.get("PREFERRED_URL_SCHEME", 'http')
app.config['DEBUG'] = True
mail = Mail(app)
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)


# db.create_all()


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        try:
            new_user = User(
                email=request.form.get('email')
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Successfully registered")
        except IntegrityError:
            flash("You've already registered!")
            return redirect(url_for('home'))
    return render_template("index.html")


@app.route('/delete', methods=['GET', 'POST'])
def delete_user():
    if request.method == 'POST':
        email1 = request.form.get('email')
        to_delete = User.query.filter_by(email=email1).first()
        db.session.delete(to_delete)
        db.session.commit()
        flash("Unsubscribed!")
    return render_template("unsubscribe.html")


def send_email(subject, sender, recipients, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.html = html_body
    with app.open_resource("img.jpg") as fp:
        msg.attach("img.jpg", "image/jpeg", fp.read())
    with app.app_context():
        mail.send(msg)


def recipes():
    now = dt.datetime.now()
    day_of_week = now.weekday()
    if day_of_week == 1:
        response = requests.get('http://www.themealdb.com/api/json/v1/1/random.php')
        response.raise_for_status()
        food_data = response.json()
        f = food_data['meals'][0]
        img = urllib.request.urlretrieve(f['strMealThumb'], 'img.jpg')
        dic = {}
        for i in range(1, 21):
            if f[f'strIngredient{i}']:
                dic.update({f[f'strIngredient{i}']: f[f'strMeasure{i}']})
        dic1 = "\n".join(f"{key}: {value}" for key, value in dic.items())
        with app.app_context(), app.test_request_context():
            hyperlink_format = url_for("delete_user", _external=True)
        users = User.query.all()
        html_body = '<html><body><pre><h2>{}</h2>' \
                    '<h3>Ingredients:</h3>{}' \
                    '<h3>Instructions:</h3>{}<br><br>' \
                    '<a href="{}">Unsubscribe</a></pre></body></html>'.format(f['strMeal'], dic1,
                                                                              f['strInstructions'],
                                                                              hyperlink_format)
        for user in users:
            send_email('New Recipe!',
                       sender=MY_EMAIL,
                       recipients=[user.email],
                       html_body=html_body
                       )


sched = BackgroundScheduler()


@app.before_first_request
def initialize():
    sched.add_job(recipes, 'interval', minutes=2)
    sched.start()


if __name__ == "__main__":
    app.run()
