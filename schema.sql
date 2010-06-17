drop table if exists users;
create table users(
    id integer primary key autoincrement,
    name string not null,
    password string not null,
    email string not null,
);

drop table if exists posts;
create table posts(
    id integer primary key autoincrement,
    author_id integer not null,
    author string not null,
    title string not null,
    body string,
    timestamp integer,
);

drop table if exists comments;
create table comments(
    id integer primary key autoincrement,
    reply_to integer not null,
    author string not null,
    author_id integer not null,
    rating integer,
    body string,
);
