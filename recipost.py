import sqlite3, datetime, time, hashlib, os, Image
from flask import Flask, request, redirect, url_for, render_template, g, session, abort
from wtforms import Form, BooleanField, TextField, PasswordField, TextAreaField, IntegerField, FileField, validators, ValidationError
from contextlib import closing
from functools import wraps
from werkzeug import secure_filename

DATABASE='recipost.db'
UPLOAD_FOLDER='static/img'
ALLOWED_EXTENSIONS=set(['jpg','png','gif','jpeg'])
SECRET_KEY='devkey'
DEBUG=True

app=Flask(__name__)
app.add_url_rule('/uploads/<filename>', 'uploaded_file', build_only=True)
app.config.from_object(__name__)

def allowed_file(filename):
    return filename.split('.')[-1] in ALLOWED_EXTENSIONS

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
    email=TextField('Email Address', [validators.required(), validators.Email()])
    password=PasswordField('Password', [validators.Required(), validators.EqualTo('password_confirm', message='Passwords must match')])
    password_confirm=PasswordField('Repeat Password')
    def validate_username(form, field):
        if query_db('select * from users where name=?', (field.data,), one=True):
            raise ValidationError('That username already exists in the database')

class LoginForm(Form):
    username=TextField('Username', [validators.required(),])
    password=PasswordField('Password', [validators.required(),])

class RecipeForm(Form):
    title=TextField('Title', [validators.required(),])
    body=TextAreaField('Recipe Body', [validators.required(),])
    image=FileField('Image File', [])

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
    def avg(l):
        l=list(l)
        return float(sum(l))/len(l)
    user_dict=query_db('select * from users where name=?', (user,), one=True)
    if user_dict:
        posts=query_db('select * from posts where author=?', (user_dict.get('name'),))
        ratings=query_db('select * from comments where reply_to in ({0})'.format(','.join('?'*len(posts))), [p['id'] for p in posts])
        ratings=dict((r,avg(c['rating'] for c in ratings if c['reply_to']==r)) for r in set(r['reply_to'] for r in ratings))
        comments=query_db('select * from comments where author=?', (user_dict.get('name'),))
        return render_template('user_page.html', posts=posts, ratings=ratings, comments=comments)
    abort(404)

@app.route('/post/<int:post_id>')
def post_page(post_id):
    post=query_db('select * from posts where id=?', (post_id,), one=True)
    if post:
        images=query_db('select * from imageref where contained_in=?', (post_id,))
        comments=query_db('select * from comments where reply_to=?', (post_id,))
        return render_template('post_page.html', post=post, comments=comments, images=images)
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
        """
        Selecting by timestamp seems really iffy but it appears to be working;
        I would prefer to be selecting by title, but titles are not unique.
        Perhaps move to uuid in the future so i can just reference that
        """
        recipe_post=query_db('select * from posts where ts=?', (recipe[-1],), one=True)
        for file in request.files.values():
            if file and allowed_file(file.filename):
                filename=secure_filename('{i}__{t}__{f}'.format(i=recipe_post['id'], t=form.title.data, f=file.filename))
                thumbname='thumb_{o}'.format(o=filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                thumb=Image.open(os.path.join(UPLOAD_FOLDER, filename))
                factor=200.0/max(thumb.size)
                thumb.resize(map(lambda d:int(factor*d), thumb.size), Image.ANTIALIAS).save(os.path.join(UPLOAD_FOLDER, thumbname))
                filedata=(g.user['name'], g.user['id'], recipe_post['id'], filename, thumbname, datetime.datetime.now())
                g.db.execute('insert into imageref (author, author_id, contained_in, filename, thumbname, ts) values (?,?,?,?,?,?)', filedata)
                g.db.commit()
        return redirect(url_for('post_page', post_id=recipe_post['id']))
    return render_template('generic_form.html', form=form)

@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post=query_db('select * from posts where id=?', (post_id,), one=True)
    if post and post.get('author')==g.user['name']:
        if request.method=='POST':
            form=RecipeForm(request.form)
            if form.validate():
                recipe=(form.body.data, form.title.data, post.get('id'))
                g.db.execute('update posts set body=?, title=? where id=?', recipe)
                g.db.commit()
                return redirect(url_for('post_page', post_id=post.get('id')))
            return render_template('generic_form.html', form=form)
        form=RecipeForm(**post)
        return render_template('generic_form.html', form=form)
    return redirect(url_for('index'))

@app.route('/confirm_delete/<int:post_id>')
@login_required
def confirm_delete(post_id):
    session['confirm_delete']=post_id
    post=query_db('select * from posts where id=?', (post_id,), one=True)
    return render_template('confirm.html', post=post)


@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post=query_db('select * from posts where id=?', (post_id,), one=True)
    if post.get('author')==g.user['name'] and session.get('confirm_delete', None)==post_id:
        session.pop('confirm_delete')
        g.db.execute('delete from posts where id=?', (post_id,))
        g.db.execute('delete from comments where reply_to=?', (post_id,))
        images=query_db('select * from imageref where contained_in=?', (post_id,))
        for image in images:
            for path in [os.path.join(UPLOAD_FOLDER, image[p]) for p in ('filename', 'thumbname',)]:
                if os.access(path, os.F_OK):
                    os.remove(path)
        g.db.execute('delete from imageref where contained_in=?', (post_id,))
        g.db.commit()
    return redirect(url_for('index'))

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

@app.route('/search', methods=['GET','POST'])
def search():
    searchterm=request.form.get('search')
    print searchterm
    if request.method=='POST' and searchterm:
        searchterm='%{0}%'.format(searchterm)
        users=query_db('select * from users where name like ?', (searchterm,))
        posts=query_db('select * from posts where body like ? or title like ?',
            (searchterm,searchterm,))
        return render_template('index.html',users=users,posts=posts)
    return redirect(url_for('index'))

if __name__=='__main__':
    app.run(host='0.0.0.0', port=8091)
