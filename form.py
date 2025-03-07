from flask import Flask, redirect, url_for, session, request, jsonify, Markup
from flask_oauthlib.client import OAuth
from flask import render_template

import pprint
import os
import sys
import json
import pymongo
from bson.objectid import ObjectId

app = Flask(__name__)

app.debug = True #Change this to False for production

app.secret_key = os.environ['SECRET_KEY']
connection_string = os.environ["MONGO_CONNECTION_STRING"]
db_name = os.environ["MONGO_DBNAME"]
oauth = OAuth(app)

client = pymongo.MongoClient(connection_string)
db = client[db_name]
collection = db['Posts']


github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'],
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],
    request_token_params={'scope': 'user:email'},
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)

def process_reply(reply, id):
    result = collection.update_one(
  { '_id' : ObjectId(id) },
  { '$push': { 'Replies': session['user_data']['login'] + " : " + reply } }
)
    print(result.matched_count)
    return

def show_posts(search):
    divs=""
    if search == "":
        for doc in collection.find():
            divs+=Markup('<div class="card">' + '<div class="card-header">' + '<h4 class="float-left">' + doc["Name"] + '</h4>')
            if 'github_token' in session and doc["Name"] == session['user_data']['login']:
                divs+=Markup('<form action="/delete" method="post">' + '<button type="submit" class="btn btn-danger float-right" name="ID" value="' + str(doc["_id"]) + '" ' + '>DELETE</button>' + '</form>')
            divs+=Markup('</div>' + '<div class="card-body">' + '<p>' + doc["Text"] + '</p>' + '</div>')
            if "Replies" in doc:
                for r in doc["Replies"]:
                    divs+=Markup('<div class="card-body reply">' + '<p>' + r + '</p>' + '</div>')
            if 'github_token' in session:
                divs+=Markup('<div class="card-footer">' + '<form class="form-inline" action="/reply" method="post">' + '<input class="form-control mr-sm-2" type="text" placeholder="Reply" name="reply">' + '<button class="btn btn-primary" name="ID" value="' + str(doc["_id"]) + '" ' + 'type="submit">' + 'Reply' + '</button>' + '</form>' + '</div>' + '</div>' + '<br>')
            else:
                divs+=Markup('</div>' + '<br>')
        return divs
    else:
        for doc in collection.find():
            if search in doc["Text"]:
                if 'github_token' in session:
                    divs+=Markup('<div class="card">' + '<div class="card-header">' + '<h4>' + doc["Name"] + '</h4>' + '</div>' + '<div class="card-body">' + '<p>' + doc["Text"] + '</p>' + '</div>' + '<div class="card-footer">' + '<form class="form-inline" action="/reply" method="post">' + '<input class="form-control mr-sm-2" type="text" placeholder="Reply" name="reply">' + '<button class="btn btn-primary" name="ID" value=' + str(doc["_id"]) + 'type="submit">' + 'Reply' + '</button>' + '</form>' + '</div>' + '</div>' + '<br>')
                else:
                    divs+=Markup('<div class="card">' + '<div class="card-header">' + '<h4>' + doc["Name"] + '</h4>' + '</div>' + '<div class="card-body">' + '<p>' + doc["Text"] + '</p>' + '</div>' + '</div>' + '<br>')
        return divs

def process_post(post):
    collection.insert_one({"Name" : session['user_data']['login'], "Text" : post})
    return

def process_deletion(id):
    collection.delete_one({"_id" : ObjectId(id)})
    return

@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/')
def testing():
    return render_template('home.html')

@app.route('/form', methods=['GET', 'POST'])
def home():
    div = show_posts("")
    return render_template('form.html', past_posts = div)

@app.route('/posted', methods=['POST'])
def posted():
    p = request.form['post']
    process_post(p)
    return redirect(url_for("form", code=307))

@app.route('/search', methods=['GET', 'POST'])
def search():
    s = request.form['search']
    div = show_posts(s)
    return render_template('form.html', past_posts = div)

@app.route('/reply', methods=['GET', 'POST'])
def reply():
    r = request.form["reply"]
    id = request.form['ID']
    process_reply(r, id)
    div = show_posts("")
    return redirect(url_for("form", code=307))

@app.route('/delete', methods=['GET', 'POST'])
def delete():
    print("deleting")
    id = request.form['ID']
    process_deletion(id)
    return redirect(url_for("form", code=307))

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login')
def login():
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='https'))

@app.route('/logout')
def logout():
    session.clear()
    return render_template('message.html', message='You were logged out')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        message = 'Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args)
    else:
        try:
            print(resp)
            session['github_token'] = (resp['access_token'], '')
            session['user_data']=github.get('user').data
            message='You were successfully logged in as ' + session['user_data']['login']
        except Exception as inst:
            session.clear()
            print(inst)
            message='Unable to login, please try again.  '
    return render_template('message.html', message=message)


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')


if __name__ == '__main__':
    app.run()
