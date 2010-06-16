import pycassa

client=pycassa.connect()
users=pycassa.ColumnFamily(client, 'recipost', 'Users', super=True)
posts=pycassa.ColumnFamily(client, 'recipost', 'Posts', super=True)
usernames=pycassa.ColumnFamily(client, 'recipost', 'UserNames')

class User:
    def __init__(self, name, email, password):
        self.id=uuid.uuid4().get_hex()
        self.name=name
        self.email=email
        self.password=hashlib.sha1(password).hexdigest()

    def dumps(self):
        return {'public_data':{
        return {'name':self.name,
                'password':self.password

class Post:
    def __init__(self, title, body):
        self.id=uuid.uuid4().get_hex()
        self.title=title
        self.body=body
        self.author=author
        self.author_id=usernames.get(author).get('id')
        self._ts=_long(int(time.time()*1e6))

