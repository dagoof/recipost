import sqlite3, datetime, time, hashlib
from flask import Flask, request, redirect, url_for, render_template, g
from contextlib import closing
from wtforms import Form, BooleanField, TextField, PasswordField, validators

DATABASE='recipost.db'
SECRET_KEY='devkey'
DEBUG=True
app=Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(DATABASE)

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur=g.db.execute(query, args)
    rv=[dict((cur.description[idx][0], value) 
        for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

class RegistrationForm(Form):
    username=TextField('Username', [validators.Length(min=4, max=25), validators.Required()])
    email=TextField('Email Address', [validators.required(),])
    password=PasswordField('Password', [validators.Required(), validators.EqualTo('password_confirm', message='Passwords must match')])
    password_confirm=PasswordField('Repeat Password')

@app.before_request
def before_request():
    g.db=connect_db()

@app.after_request
def after_request(response):
    g.db.close()
    return response

@app.route('/')
def index():
    return render_template('index.html', users=(user for user in query_db('select * from users')))

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form=RegistrationForm(request.form)
    if request.method=='POST' and form.validate():
        user=[form.username.data, hashlib.sha256(form.password.data).hexdigest(), form.email.data]
        g.db.execute('insert into users (name, password, email) values (?,?,?)', user)
        g.db.commit()
        return redirect(url_for('index'))
    return render_template('registration.html', form=form)


if __name__=='__main__':
    app.run(host='0.0.0.0', port=8091)
