from flask import Flask, render_template, request, make_response, session, redirect, flash, url_for, send_from_directory
from flaskext.mysql import MySQL
from werkzeug.utils import secure_filename
import os
from os.path import join, dirname, realpath
from mutagen.mp3 import MP3


UPLOAD_FOLDER = join(dirname(realpath(__file__)), './static/songs')
UPLOAD_FOLDER_IMAGES = join(dirname(realpath(__file__)), './static/images/songs')
ALLOWED_EXTENSIONS = set(['mp3', 'mp4', 'woff', 'jpg', 'png', 'mpeg'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER_IMAGES'] = UPLOAD_FOLDER_IMAGES

mysql = MySQL(app)

#gegevens ingeven voor database
app.config["MYSQL_DATABASE_HOST"] = "localhost"
app.config["MYSQL_DATABASE_DB"] = "project"
app.config["MYSQL_DATABASE_USER"] = "root"
app.config["MYSQL_DATABASE_PASSWORD"] = "thibault"
app.secret_key = os.urandom(20)
app.run(debug=True)

image = ""
artist = ""
title = ""
path = ""
length = "3:"

def get_data(sql, params=None):
    conn = mysql.connect()
    #soort winkelkar om gegevens uit te kiezen
    cursor = conn.cursor()

    try:
        cursor.execute(sql, params)
    except Exception as e:
        print(e)
        return False

    results = cursor.fetchall()
    db_data = []

    for row in results:
        #lijst wordt in een lijst gestopt, 1 row = 1 lijst
        db_data.append(list(row))

    print(db_data)

    #afsluiten connectie en winkelkar
    cursor.close()
    conn.close()

    return db_data

@app.route('/')
def home():
    user_name = request.cookies.get("user")
    if user_name == "":
        return redirect("/logout")
    if checkLogin():
        order_by= "s" + "title"
        order= "asc"
        songs = get_data("select s.title, s.length,s.artist,substr(s.date,1,10) from songs as s join songs_has_user as su on su.songID = s.songID join user as u on u.userID = su.userID where u.name like %s order by %s %s;",
                         (user_name, order_by,order))
        titels = get_data("SHOW columns FROM songs where field not like %s and field not like 'Image' and field not like 'path'", '%id%')
        if songs.__len__() <= 0:
            if user_name == "":
                return redirect("/logout")
            flash("uw heeft nog geen muziek")
            return redirect("/upload_music")
        return render_template("home.html", songs=songs, titels=titels)
    else:
        return redirect("/login")


@app.route('/login/', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        naam = request.form.get('username')
        login = get_data("SELECT count(*) from user where name = %s and binary password = %s;", (naam, password))
        global user_name
        user_name = naam
        print(user_name)
        if login[0][0] > 0:
            session['loggedin'] = 1
            antwoord = make_response(redirect("/"))
            antwoord.set_cookie('user', user_name)
            return antwoord
        else:
            return render_template("login.html", Error=True)
    if checkLogin():
        return redirect("/")
    return render_template("login.html")


@app.route('/registreer/', methods=['POST', 'GET'])
def registreer():
    html = render_template('registreer.html')
    if request.method == 'POST':
        user_name = request.form["username"],
        pwd = request.form["password"],
        # email = request.form["email"]
        connection = mysql.get_db()
        cursor = connection.cursor()
        query = "INSERT INTO user(name, password) VALUES(%s, binary %s)"
        cursor.execute(query, (user_name, pwd))
        connection.commit()
        return redirect("/login")
    else:
        return html


def checkLogin():
    if 'loggedin' in session:
        return True
    else:
       return False


@app.route('/logout/')
def logout():
    if checkLogin():
        session.pop('loggedin')
        return redirect("/")
    else:
        return redirect("/login/")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_music/', methods=['POST', 'GET'])
def upload_music():
    user_name = request.cookies.get("user")
    if user_name == "":
        return redirect("/logout")
    if checkLogin():
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file part')
                return redirect("/error/")
            file = request.files['file']
            image = request.files['image']
            artist = request.form['artist']
            title = request.form['title']
            if artist == '':
                artist = 'Unknown'

            # if user does not select file, browser also
            # submit a empty part without filename
            if file.filename == '':
                flash('No selected file')
                return redirect("/error/")
            print(image.filename)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                audio = MP3(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                length = round(((audio.info.length) // 60) + ((audio.info.length % 60) / 100), 2)
                length= str(length).replace(".", ":")
                print(image.filename)
                print("test")

                if image.filename != '':
                    print(image.filename)
                    image_filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER_IMAGES'], image_filename))

                connection = mysql.get_db()
                cursor = connection.cursor()
                userID = get_data("select userID from user where name like %s;", user_name)
                if title == '':
                    title =filename.replace(".mp3", "").replace("_", " ")

                query = "INSERT INTO songs(title, length, artist, image, path) VALUES(%s,%s,%s,%s,%s)"
                cursor.execute(query, (title, length, artist, image_filename, filename))
                connection.commit()

                songID = get_data("select songID from songs order by songID DESC limit 1")

                query = "INSERT INTO songs_has_user(songID, UserID) VALUES(%s,%s)"
                cursor.execute(query, (songID, userID))
                connection.commit()
                return redirect("/")
        return render_template("upload_music.html")
    else:
        return redirect("/login/")


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    user_name = request.cookies.get("user")
    if user_name == "":
        return redirect("/logout")
    else:
        song = get_data("SELECT Image, artist, title, path, length from songs where title = %s;", (filename))
        image = song[0][0]
        artist = song[0][1]
        title = song[0][2]
        path = song[0][3]
        length = song[0][4]
        antwoord = make_response(render_template("uploads.html", path=path, image=image, artist=artist, title=title))
        antwoord.set_cookie('image', image)
        antwoord.set_cookie('artist', artist)
        antwoord.set_cookie('title', title)
        antwoord.set_cookie('length', length)
        antwoord.set_cookie('path', path)
        antwoord.set_cookie('current length', "0")
        return antwoord


@app.route('/error/')
def error():
    return render_template('error.html')


@app.route('/data/')
def data():
    user_name = request.cookies.get("user")
    if user_name == "":
        return redirect("/login")
    else:
        userID = get_data("select userID from user where name like %s;", user_name)
        decibels = get_data("SELECT * FROM data where userID = %s and sensorID = %s", (userID, 1))
        LDR = get_data("SELECT * FROM data where userID = %s and sensorID = %s", (userID, 2))
        colors = ['#0095FF', 'red']
        return render_template('data.html', decibels=decibels, LDR=LDR, Colors=colors)


@app.route('/settings/')
def settings():
    user_name = request.cookies.get("user")
    if user_name == "":
        return redirect("/login")
    else:
        return render_template('settings.html')


@app.errorhandler(404)
def page_not_found(e):
    return redirect("/error")


if __name__ == '__main__':
    app.run(debug=True)
