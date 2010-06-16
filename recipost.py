from flask import Flask, request, redirect, url_for, render_template
import pycassa

client=pycassa.connect()
users=pycassa.ColumnFamily(client, 'recipost', 'Users', super=True)
posts=pycassa.ColumnFamily(client, 'recipost', 'Posts', super=True)
usernames=pycassa.ColumnFamily(client, 'recipost', 'UserNames')
app=Flask(__name__)

def get_user(username):
    try:
        return usernames.get(username)
    except:
        return  {}

@app.route('/')
def index():
    return 'hello world'



if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port=8091)
