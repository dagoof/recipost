from flask import Flask, request, redirect, url_for, render_template
import sqlite3
from contextlib import closing
import time

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

@app.before_request
def before_request():
    g.db=connect_db()

@app.route('/')
def index():
    return 'hello world'



if __name__=='__main__':
    app.run(host='0.0.0.0', port=8091)
