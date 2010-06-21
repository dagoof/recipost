import sqlite3, datetime, time, hashlib
from flask import Flask, request, redirect, url_for, render_template, g, session, abort
from wtforms import Form, BooleanField, TextField, PasswordField, TextAreaField, IntegerField, validators
from contextlib import closing
from functools import wraps

DATABASE='recipost.db'
SECRET_KEY='devkey'
DEBUG=True
app=Flask(__name__)
app.config.from_object(__name__)

def do_markdown(s):
    from markdown import markdown
    from jinja2.utils import Markup
    return Markup(markdown(s.encode('utf-8')).decode('utf-8'))

app.jinja_env.filters['markdown']=do_markdown

def adapt_datetime(ts):
    return time.mktime(ts.timetuple())

sqlite3.register_adapter(datetime.datetime, adapt_datetime)

def connect_db():
    return sqlite3.connect(DATABASE)

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource(DATABASE) as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur=g.db.execute(query, args)
    rv=[dict((cur.description[idx][0], value) 
        for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv

class RegistrationForm(Form):
    username=TextField('Username', [validators.Length(min=4, max=25), validators.Required()])
    email=TextField('Email Address', [validators.required(), validators.Email()])
    password=PasswordField('Password', [validators.Required(), validators.EqualTo('password_confirm', message='Passwords must match')])
    password_confirm=PasswordField('Repeat Password')

class LoginForm(Form):
    username=TextField('Username', [validators.required(),])
    password=PasswordField('Password', [validators.required(),])

class RecipeForm(Form):
    title=TextField('Title', [validators.required(),])
    body=TextAreaField('Recipe Body', [validators.required(),])

class CommentForm(Form):
    body=TextAreaField('Comment', [validators.required(),])
    rating=IntegerField('Rating', [validators.required(),])


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, 'user', None):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def before_request():
    g.db=connect_db()
    g.user=None
    if 'username' in session:
        g.user=query_db('select * from users where name=?', (session['username'],), one=True)

@app.after_request
def after_request(response):
    g.db.close()
    return response

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'),404

@app.route('/')
def index():
    return render_template('index.html',
        users=query_db('select * from users'),
        posts=query_db('select * from posts'),)

@app.route('/register', methods=['GET', 'POST'])
def register_user():
    form=RegistrationForm(request.form)
    if request.method=='POST' and form.validate():
        user=[form.username.data, hashlib.sha256(form.password.data).hexdigest(), form.email.data]
        g.db.execute('insert into users (name, password, email) values (?,?,?)', user)
        g.db.commit()
        return redirect(url_for('index'))
    return render_template('generic_form.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    form=LoginForm(request.form)
    if request.method=='POST':
        form_user={'name':form.username.data, 'password':hashlib.sha256(form.password.data).hexdigest()}
        user=query_db('select * from users where name=?', (form_user.get('name'),), one=True)
        if user and user.get('password')==form_user.get('password'):
            session['username']=user.get('name')
            return redirect(url_for('index'))
    return render_template('generic_form.html', form=form)

@app.route('/user/<user>')
def user_page(user):
    user_dict=query_db('select * from users where name=?', (user,), one=True)
    if user_dict:
        posts=query_db('select * from posts where author=?', (user_dict.get('name'),))
        return render_template('user_page.html', posts=posts)
    abort(404)

@app.route('/post/<int:post_id>')
def post_page(post_id):
    post=query_db('select * from posts where id=?', (post_id,), one=True)
    if post:
        comments=query_db('select * from comments where reply_to=?', (post_id,))
        return render_template('post_page.html', post=post, comments=comments)
    abort(404)

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_recipe():
    form=RecipeForm(request.form)
    if request.method=='POST' and form.validate():
        recipe=(g.user['id'], g.user['name'], form.title.data, form.body.data, datetime.datetime.now())
        g.db.execute('insert into posts (author_id, author, title, body, ts) values (?,?,?,?,?)', recipe)
        g.db.commit()
        return redirect(url_for('index'))
    return render_template('generic_form.html', form=form)

@app.route('/comment/<int:post_id>', methods=['GET','POST'])
@login_required
def comment(post_id):
    form=CommentForm(request.form)
    if request.method=='POST' and form.validate():
        recipe=(post_id, g.user['name'], form.rating.data, form.body.data, datetime.datetime.now())
        g.db.execute('insert into comments (reply_to, author, rating, body, ts) values (?,?,?,?,?)', recipe)
        g.db.commit()
        return redirect(url_for('post_page', post_id=post_id))
    return render_template('generic_form.html', form=form)


if __name__=='__main__':
    app.run(host='0.0.0.0', port=8091)
