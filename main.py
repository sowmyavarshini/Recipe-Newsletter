import requests
import smtplib
import datetime as dt
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import urllib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from flask_apscheduler import APScheduler
import tzlocal
from dotenv import load_dotenv
import os

load_dotenv()

MY_EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")

app = Flask(__name__)
Secret_key = os.getenv("SECRET_KEY")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", Secret_key)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
schedule = APScheduler()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)


db.create_all()


def recipes():
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
    hyperlink_format = '<a href="{}">{}</a>'.format('http://127.0.0.1:5000/delete', 'Unsubscribe')
    contents = f"{f['strMeal']}\n\nINGREDIENTS:\n\n{dic1}\n\nINSTRUCTIONS:\n\n {f['strInstructions']}\n\n{hyperlink_format}"
    html = """\
           <html>
             <head></head>
             <body>
               <pre>
               <h2>""" + f['strMeal'] + """</h2><h3>Ingredients:</h3>""" + dic1 + """<h3>Instructions:</h3>""" + f[
        'strInstructions'] + \
           """<br>""" + hyperlink_format + """
               </pre>
             </body>
           </html>
           """
    users = User.query.all()
    for user in users:
        message = MIMEMultipart()
        message['from'] = MY_EMAIL
        message['to'] = user.email
        message['subject'] = "New Recipe!"
        message.attach(MIMEText(html, 'html'))
        message.attach(MIMEImage(Path('img.jpg').read_bytes()))
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.ehlo()
            connection.starttls()
            connection.login(user=MY_EMAIL, password=PASSWORD)
            connection.send_message(message)


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
        email = request.form.get('email')
        to_delete = User.query.filter_by(email=email).first()
        db.session.delete(to_delete)
        db.session.commit()
        flash("Unsubscribed!")
    return render_template("unsubscribe.html")


if __name__ == "__main__":
    schedule.add_job(id='Job1', func=recipes, trigger='cron', day_of_week='tue', hour=5, minute=30)
    schedule.start()
    app.run(debug=True, use_reloader=False)
