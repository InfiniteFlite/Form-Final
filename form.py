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
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

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

def show_posts(search):
    divs=""
    if search == "":
        for doc in collection.find():
            divs+=Markup('<div class="card">' + '<div class="card-header">' + '<h4>' + doc["Name"] + '</h4>' + '</div>' + '<div class="card-body">' + '<p>' + doc["Text"] + '</p>' + '</div>' + '<div class="card-footer">' + 'This is a footer' + '</div>' + '</div>' + '<br>')
        return divs
    else:
        for doc in collection.find():
            if search in doc["Text"]:
                divs+=Markup('<div class="card">' + '<div class="card-header">' + '<h4>' + doc["Name"] + '</h4>' + '</div>' + '<div class="card-body">' + '<p>' + doc["Text"] + '</p>' + '</div>' + '<div class="card-footer">' + 'This is a footer' + '</div>' + '</div>' + '<br>')
        return divs

def process_post(post):
    collection.insert_one({"Name" : session['user_data']['login'], "Text" : post})
    return

@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/', methods=['GET', 'POST'])
def home():
    div = show_posts("")
    return render_template('home.html', past_posts = div)

@app.route('/posted', methods=['POST'])
def posted():
    p = request.form['post']
    process_post(p)
    return redirect(url_for("home", code=307))

@app.route('/search', methods=['GET', 'POST'])
def search():
    s = request.form['search']
    div = show_posts(s)
    return render_template('home.html', past_posts = div)

@app.route('/test')
def testing():
    return render_template('testing.html')

@app.route('/login')
def login():
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='http'))

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
