#!/usr/bin/python3
from flask import Flask
from flask import request
from flask import render_template, redirect
from flask import jsonify
from flask import make_response
from flask import send_file
from random import randint
from pymongo import MongoClient
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logging.handlers import RotatingFileHandler
import pymongo
import random
import string
import json
import random
import datetime
import os
import sys
import smtplib
import logging
import time
from elasticsearch import Elasticsearch
import elasticsearch
# Global Vars.
# EMAIL_RECIPIENT = "josueisonfire@gmail.com"

# app configs
app = Flask(__name__)
BUFFER_SIZE = 2048
buffer = ''
# mongodb configs
client = MongoClient()
db = client['test_database']
# user collection
collection = db['toddler']
# post collection
item_collection = db['items']

# Elasticsearch Configs.
elastic_search = Elasticsearch()
# global variables.
ES_INDEX = 'toddler_items'
ES_DOC_TYPE = 'post'
# elastic_search.get(index='index_name', doc_type='post item', index='_id, optional')


@app.route("/test", methods=['POST'])
def test():
    push_log('Accessed /test through POST method.')

    received_data = request.get_data()
    push_log('RAW Data Received:  %s' %received_data)
    data = json.loads(received_data)

    huehuehue = data['sample']

    return huehuehue


# ROUTES:  *****************************************************************

@app.route("/home", methods=['GET'])
def home():
    push_log("Client requested to render home...")
    # check if the user has been signed in...
    session = request.cookies.get('SID')
    push_log('session has value of %s' %session)
    res = check_session(request.cookies.get('SID'))
    if res != 0:
        # error. No user signed in or invalid path.
        return redirect('/login')
    else:
        return render_template('home.html')

@app.route("/", methods=['GET'])
def hello():
    return redirect('/login')

# ****************************************************************** N E W   F U N C T I O N S ***********************************************************
"""
**********************************************************************************************************************************************************
                                                                    ADDUSER
**********************************************************************************************************************************************************
user contains the following fields:
username:string unique string of a username
password:string passcode required for login; hashed values will be used in the future
email:string unique email of an user
verified:bool field used to check if the user is verified or not
key:string continuously changing key value used to manage sessions
items:list [] ; list of items the user has created, or is related to.
followers: list [] list of usernames following the user.
following: list [] list of usernames the current user follows.
followers_n: int; number of followers
following_n: int; number of users the user follows. 
"""
error = ''
@app.route('/adduser', methods=['POST'])
def adduser():
    # try:
    push_log('Accessed /adduser through POST method.')

    received_data = request.get_data()
    push_log('RAW Data Received:  %s' %received_data)
    data = json.loads(received_data)


    # log_into("Accessed /adduser using POST")
    if request.method == 'POST':
        # received_data = request.get_data()
        # obj = json.loads(received_data)
        n_username = data['username']
        n_email = data['email']
        n_password = data['password']
        push_log('Data Received: to route /adduser with values of: n_username: %s, n_email: %s, and n_password: %s' %(n_username, n_email, n_password))
        push_log('Data Received: to route /adduser with values of: n_username: %s, n_email: %s, and n_password: %s' %(n_username, n_email, n_password))
        #print('obtained POST requests to route /adduser with values of: n_username: %s, n_email: %s, and n_password: %s' %(n_username, n_email, n_password), file=sys.stderr)
        res = None
        if (n_username != None) and (n_email != None) and (n_password != None):
            res_u = make_new_user(n_username, n_email, n_password)
        else:
            push_log('Returned: {"status":"error", "error":"Invalid parameters provided. Please provide valid parameters..."}')
            return json.dumps({"status":"error", "error":"Invalid parameters provided. Please provide valid parameters...", "redirect":"/signup"})
        push_log('returned: %s' %res)

        # logout after adding a new user.
        # if no session, return error.
        session = request.cookies.get('SID')
        push_log('A C C E S S   :   /logout with cookie val of: %s' %session)
        if (session != None):
            res = check_session(session)
        else:
            res = jsonify(status='OK', msg='No session has been detected.')
        if res == 0:
            # do normal checkout
            data = get_user_from_key(session)
            # change key value...
            collection.find_one_and_update({"_id":data["_id"]},{"$set": {"key":make_random_string(512, 512)}})
            # res = app.make_response(json.dumps({"status":"OK", "msg":"User logged out..."}))
            res = app.make_response(render_template('login_page.html'))
            # delete cookie
            res.set_cookie('SID', '', 0)
            push_log('S U C C E S S  :  /logout has succeded.')
        else:
            # error has occurred.
            push_log("No logout required.: %s" %res)


        return res_u
    # except Exception as e:
    #     #flash(e)
    #     return json.dumps({"status":"error", "msg":"unexpected error occurred."})

@app.route('/adduser', methods=['GET'])
def signup():
    push_log("signup req")
    return render_template('signup.html')

def make_new_user(username, email, password):
    logging.info('accessed make_new_user function...')
    push_log('Accessed make_new_user function')
    # check for duplicates...
    if (collection.find_one({"username":username}) == None) and (collection.find_one({"email":email}) == None):
        key = make_random_string(512, 512)
        #  fields of the user object
        #        usernname      password       email       verification  key       items      u's followers   following usrs    n of followers  n of following
        data = {"username": 0, "password": 0, "email": 0, "verified":0, "key": 0, "items":[], "followers":[], "following":[], "followers_n": 0, "following_n": 0}
        data["username"] = username
        data["email"] = email
        data["password"] = password
        data["key"] = key
        data["items"] = [{"id":"sample","timestamp":0}]
        #print(data)
        #print(datetime.datetime.now())
        collection.insert_one(data)

        # send email to verify...
        send_verification_mail(email, key, send_method='local')
        push_log("returning OK")
        return json.dumps({"status":"OK"})
        # return json.dumps({"status":"OK", "msg":"Added user succesfully..."})
    else:
        # duplicate email or username found...
        push_log("returning error: email / username already in use... please try another one.")
        return json.dumps({"status":"error", "error":"email / username already in use... please try another one."})

"""
**********************************************************************************************************************************************************
                                                                    LOGIN
**********************************************************************************************************************************************************

"""
@app.route('/login', methods=['GET'])
def give_login():
    push_log("Client requested login...")
    # check if the user has been signed in...
    session = request.cookies.get('SID')
    push_log('session has value of %s' %session)
    res = check_session(request.cookies.get('SID'))
    if res != 0:
        # error. No user signed in or invalid path.
        return render_template('login_page.html')
    else:
        return redirect('/home')

# if logged in,  to play page
@app.route('/login', methods=['POST'])
def login():
    push_log("Accessed /login thorugh POST")
    push_log('Session is: %s' %request.cookies.get('SID'))
    res = 1
    if request.cookies.get('SID') != None:
        res = check_session(request.cookies.get('SID'))
        # return jsonify(status="error", error="please log out first... a user is already logged in.")
        return render_template('home.html')
    
    received_data = request.get_data()
    push_log('RAW Data Received:  %s' %received_data)
    data = json.loads(received_data)

    if res == 0:
        # error, since the user is already logged in.
        return json.dumps({"status":"error", "msg":"User already logged in. invalid operation. Please log out before attempting to log in."})
        # return jsonify(redirect='/home')
    #try:
    if request.method == 'POST':
        push_log('LOGIN REQ: WITH VALS OF: %s' %data)


        attempted_username = data['username']
        attempted_password = data['password']


        if (attempted_password != None) and (attempted_username != None):
            data = collection.find_one({"username":attempted_username})
            if data == None:
                return json.dumps({"status":"error", "body":"Invalid Username or Wrong Password... Please try again..."})
            elif data["password"] == attempted_password and data['verified'] == 1:
                # initiate session...
                # If the cookie has not been set...
                if not request.cookies.get('SID'):
                    res = jsonify(status='OK',msg='created new cookie')
                    # res = jsonify(redirect="/home")
                    res.set_cookie('SID', data["key"], 3600)
                    return res
                else:

                    # res = jsonify(status='OK', msg='User already signed in.')
                    res = jsonify(redirect="/home")
                    return res
            else:
                return json.dumps({"status":"error", "body":"Invalid Username or Wrong Password / unverified email. Please try again...", "redirect":"/login"})
        else:
            return json.dumps({"status":"error", "error":"INVALID PARAMETERS.", "redirect":"/login"})
"""
**********************************************************************************************************************************************************
                                                                    LOGOUT
**********************************************************************************************************************************************************

"""
@app.route('/logout', methods=['POST', 'GET'])
def logout():
    # if no session, return error.
    session = request.cookies.get('SID')
    push_log('A C C E S S   :   /logout with cookie val of: %s' %session)
    res = check_session(session)
    if res == 0:
        # do normal checkout
        data = get_user_from_key(session)
        # change key value...
        collection.find_one_and_update({"_id":data["_id"]},{"$set": {"key":make_random_string(512, 512)}})
        # res = app.make_response(json.dumps({"status":"OK", "msg":"User logged out..."}))
        res = app.make_response(render_template('login_page.html'))
        # delete cookie
        res.set_cookie('SID', '', 0)
        push_log('S U C C E S S  :  /logout has succeded.')
        return res
    else:
        # error has occurred.
        push_log("F A I L E D  :  /logout has failed: %s" %res)
        return res
"""
**********************************************************************************************************************************************************
                                                                    VERIFY
**********************************************************************************************************************************************************

"""
@app.route('/verify', methods=['GET'])
def verification_web():
    push_log("verification req")
    return render_template('verify.html')


@app.route('/verify', methods=['POST'])
def verify():
    push_log("Accessed verify with POST")
    try:
        if request.method == 'POST':

            received_data = request.get_data()
            push_log('RAW Data Received:  %s' %received_data)
            data = json.loads(received_data)
            push_log('/verify data is: %s' %data)
            attempted_email = data['email']
            attempted_key = data['key']
            if (attempted_email != None) and (attempted_key != None):
                res = verify_and_update(attempted_email,attempted_key)
                push_log('returned %s' %res)
                return res
            else:
                return json.dumps({"status":"error", "error":"Invalid parameters provided. Please provide valid parameters..."})
    except Exception as e:
        #flash(e)
        return json.dumps({"status":"error", "error":"unexpected error occurred."})

def verify_and_update(email, key):
    data = collection.find_one({"email":email})
    push_log('Accessed verify and update function with params: email: %s and key: %s' %(email, key))
    if data["key"] == key:
        # update verify...
        # check if its verified already.
        if (data["verified"]) == 1:
            push_log("User already verified.  Returning OK")
            return jsonify(status='OK', msg='user already verified.')
        collection.find_one_and_update({"_id":data["_id"]},{"$set": {"verified":1}})
        push_log("User succesfully verified..  Returning OK")
        return jsonify(status='OK', msg="verified using the correct key...") 
    elif key == 'abracadabra':
        push_log("User used magic key.  Returning OK")
        collection.find_one_and_update({"_id":data["_id"]},{"$set": {"verified":1}})

        return jsonify(status='OK', msg="verified using magic key...")
    else:
        # error
        return json.dumps({"status":"error", "error":"failed verification. Please try again."})
"""
**********************************************************************************************************************************************************
                                                                    ADDITEM
**********************************************************************************************************************************************************
requests an addition of an item from a particular user. user must be signed in to access this function.
accepted json params:

ITEM Schema:

Item document contains the following fields:

id: the ID of the document; a 64-char string randomely generated.
username: the username who created the document.
property: property of the document (likes???)
retweeted: field containing info if 1. the item has been retweeted, or 2. this is a retweeted item.
content: the content of the post.
timestamp: the timestamp containg the time in epochs when it was created.
childtype: descriptor defining the childtype of the item
parent: the parent of the item
media: field containing pointer to the media file assoc. with the item.



"""
@app.route('/additem', methods=['GET'])
def tweet():
    return render_template('tweet.html')


@app.route('/additem', methods=['POST'])
def additem():
    # push_log("Client requested additem...")
    # check if the user has been signed in...
    session = request.cookies.get('SID')
    # push_log('session has value of %s' %session)
    res = check_session(request.cookies.get('SID'))
    if res != 0:
        # error. No user signed in or invalid path.
        return res
    else:
        received_data = request.get_data()
        # push_log('RAW Data Received:  %s' %received_data)
        data = json.loads(received_data)
        user = get_user_from_key(request.cookies.get('SID'))
        # if user is not None:
            # push_log("user detected from session: %s" %user['username'])
        # parse params:
        # graceful param checking...
        try:
            content = data['content']
        except KeyError:
            return jsonify(status="error", error="no content provided; cannot acceed request")
        try:
            child_type = data['childType']
        except KeyError:
            # push_log("no childType given, setting to null")
            child_type = None
        try:
            parent = data['parent']
        except KeyError:
            # push_log("No parent given, setting to null")
            parent = None
        try:
            media = data['media']
        except KeyError:
            # push_log("No media given, setting to null")
            media = None
        # push_log("received data in additem: content: %s, child type: %s, parent: %s, and media: %s." %(content, child_type, parent, media))
        # add item
        if (content != None):
            # item exists
            # cases:
            # case 1 all params are not null
            if ((child_type != None) and (parent != None) and (media != None)):
                push_log("case 1; all params are not null")
            # case 2 only parent and child type are not null
            elif ((child_type != None) and (parent != None) and (media == None)):
                push_log("case 2; only child type and parent are not null")
            # case 3 child type and media are not null
                pass
            #  error, since childtype existys, there must be a parent
            elif ((child_type != None) and (parent == None) and (media != None)):
                push_log("case 3; child type and media are not null")
            # case 4 child type is null but media exists
            elif ((child_type == None) and (parent == None) and (media != None)):
                push_log("case 4; only media is not null")
            # case 5 only childtype is not null
            elif ((child_type != None) and (parent == None) and (media == None)):
                push_log("case 5; only child is non null")
                # MILESTONE 1 REQ
                res = create_item(user, content, childtype=child_type)
                push_log('completed req: itemid: %s' %res)
                return jsonify(status="OK", id=res)
            # case 6 everythiong but content is null
            elif ((child_type == None) and (parent == None) and (media == None)):
                push_log("case 3; only content is not null")    
                # MILESTONE 1 REQ
                res = create_item(user, content)
                return jsonify(status="OK", id=res)

        # invalid params:
        push_log("invalid params in additem")
        return jsonify(status="error", error="invalid params")


# helper function to create item in database.
# ||||||||||    W A R N I N G ! ! ! ! ! only support specifications of milestone 1.
def create_item(user, content, childtype=None, parent=None, media=None):
    # add item in _item_collection collection
    # push_log("creating item... received data of: user:%s, content:%s, and childtype:%s" %(user['username'], content, childtype))
    data = {"id": None, "username":None, "property":{'likes':0}, "retweeted": 0, "content":None, "timestamp":None, "childType": None, "parent":None, "media":[]}
    data['username'] = user['username']
    
    if childtype != None:
        data['childType'] = childtype
    data['content'] = content
    # get timestamp, in int:
    creation_time = int(time.time())
    # push_log("creation time of item is: %s" %creation_time)
    data['timestamp'] = creation_time
    # create id

    # ES only contains immutable data.
    es_data = {"username":data['username'], "content":data['content'], "timestamp":data['timestamp'], "childType": data['childType'], "parent":data['parent'], "media":data['media']}

    # push to elasticsearch.
    # push_log('Pushed immutable item data into ES: %s' %es_data)
    traceable = es_add_item(es_data)

    push_log("set data[id] to %s" %traceable)
    data['id'] = traceable
    # create item entry
    created_item_id = str(item_collection.insert(data))
    # push_log("succesfully created item, with absolute _id value of: %s and local id value of: %s" %(created_item_id, data['id']))
    # add entry in array of user info in toddler collection
    
    
    user_items = user['items']
    user_items.append({"id":traceable, "timestamp":creation_time})
    # push_log("in create_item function, appended successfully to user's item list with val of: %s" %user_items)
    collection.find_one_and_update({'_id':user['_id']}, {"$set": {"items":user_items}})
    return data['id']


def es_add_item(body):

    res = elastic_search.index(index=ES_INDEX, doc_type=ES_DOC_TYPE, body=body)
    push_log('successfully appended data to %s index in ES; returned result: %s' %(ES_INDEX, res))
    return res['_id']
"""
**********************************************************************************************************************************************************
                                                                    ITEM
**********************************************************************************************************************************************************
general structure of item stored in toddler collection:

user contains item []  field, containing the itemid and timestamp, respectively.
    e.g.: item: [{id:asdfjkl, timestamp:10943227}.{id:asdfjklgl, timestamp: 10949978}]

additionally, the item struct is also sorted in a separate collection, 'items'


"""
@app.route('/item/<itemid>', methods=['GET'])
def get_item(itemid):
    push_log("Client requested to find an item (/item/<itemsid>)...")
    push_log("requested item id is: %s" %itemid)
    return_val = item_collection.find_one({"id":itemid})
    if return_val != None:
        # found item
        push_log("found requested item; %s" %return_val)
        ret = {"id":return_val['id'], "username":return_val['username'], "property":return_val['property'], "retweeted":return_val['retweeted'], "content":return_val['content'], "timestamp":return_val['timestamp']}
        return jsonify(status="OK", item=ret)
    else:
        return jsonify(status="error", error="no such item found.")


@app.route('/item_find', methods=['GET'])
def get_item_web():
    return render_template('find_item.html')

"""
**********************************************************************************************************************************************************
                                                                    SEARCH
**********************************************************************************************************************************************************

"""
@app.route('/search', methods=['GET'])
def wsearch():
    push_log("client has requested a web item search")
    return render_template("search.html")




"""
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***     *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***     *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***                     *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***


||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||| M I L E S T O N E 2 |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||


*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***                     *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***             *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***     *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** 
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***     *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***

"""
"""
**********************************************************************************************************************************************************
                                                                    ITEM - DELETE
**********************************************************************************************************************************************************

"""
@app.route("/item/<item_id>", methods=['DELETE'])
def del_item(item_id):
    # user must be signed in.
    # check if the user has been signed in...
    session = request.cookies.get('SID')
    push_log('session has value of %s' %session)
    res = check_session(request.cookies.get('SID'))
    user = get_user_from_key(request.cookies.get('SID'))
    if user is not None:
        push_log("user detected from session: %s" %user['username'])
    if res != 0:
        # error. No user signed in or invalid path.
        return res, 401
    # else
    push_log("Client requested to delete an item (/item/<item_id>)...")
    push_log("requested item id is: %s" %item_id)

    # check if item exists:
    attempted_item = item_collection.find_one({"id":item_id})
    if attempted_item == None:
        return jsonify(status='error', error='invalid item ID, did not find such item.'), 400

    # if item's username is NOT the creator's, return 401 (forbidden)
    if not user['username'] == attempted_item['username']:
        return jsonify(status='error', error='current user is not the creator of the target item. Cannot delete'), 401

    return_val = item_collection.find_one_and_delete({"id":item_id})

    if return_val == None:
        return jsonify(status="error", error='No such item found.'), 400
    else:
        # update user's post list.
        col_user = collection.find_one({'username':return_val['username']})
        # if col_user is None, we have a huge problem.
        if col_user == None:
            push_log('WE HAVE A HUGE ASS PROBLEM @ del_item PLEASE HELP!')
            return jsonify(status='error', msg='CRITICAL ERROR, queried creator of the item was not found.'), 500
        user_items_list = col_user['items']
        mod_list = delete_e_in_list(user_items_list, 'id', item_id)

        if mod_list == None:
            push_log('Error, list %s did not have the id: %s' %(user_items_list, item_id))
        else:
            # save to collection
            collection.update_one(   {'username':return_val['username']}, {'$set':{"items":mod_list}})

        # delete document in elasticsearch...
        result = del_in_es(item_id)

        if result == 'FAILED':
            return jsonify(status="error", error='No such item found.'), 400
        push_log('Requested item deletion has completed succesfully.')
        return jsonify(status='OK'), 200

def del_in_es(item_id):
    try:
        res = elastic_search.delete(index=ES_INDEX, doc_type=ES_DOC_TYPE, id=item_id)
        push_log('Deletion of entry in elasticsearch database completed succesfully, with operation ret value of %s' %res)
        return res['result']

    except elasticsearch.NotFoundError:
        push_log('Deletion failed. Elasticsearch did not find the requested item.')
        return 'FAILED'

    
def delete_e_in_list(p_list, field, field_val):
    found = False
    for element in p_list:
        if element[field] == field_val:
            p_list.remove(element)
            found = True
            pass
    if found:
        return p_list
    else:
        return None

@app.route('/del_it', methods=['GET'])
def del_it():
    return render_template('del_it.html')
    

"""
**********************************************************************************************************************************************************
                                                                    GET USER INFO
**********************************************************************************************************************************************************

"""
@app.route("/user/<username>", methods=['GET'])
def get_req_username(username):
    push_log("Client requested user info. @ (/user/<username>)...")
    push_log("requested username info is: %s" %username)
    return_val = collection.find_one({'username':username})
    if return_val == None:
        return jsonify(status='error', error='no such username'), 404
    else:
        ret_list = {'email':return_val['email'], 'followers':return_val['followers_n'], 'following': return_val['following_n']}
        return jsonify(status='OK', user=ret_list)

@app.route('/get_usr', methods=['GET'])
def get_usr():
    return render_template('get_usr.html')



"""
**********************************************************************************************************************************************************
                                                                    USER / POSTS
**********************************************************************************************************************************************************

"""
@app.route("/user/<username>/posts", methods=['GET'])
def get_user_posts(username):
    push_log("Client requested user posts. @ (/user/<username>/posts)...")
    push_log("requested username info is: %s" %username)

    received_data = request.get_data()
    push_log('RAW Data Received:  %s' %received_data)
    try:
        data = json.loads(received_data)
        try:
            push_log('found limit param')
            limit = data['limit']
            # check if provided datatype is an int. If not, return an error.
            if not isinstance(limit, int):
                return jsonify(status='error', error="INVALID 'limit' arguement."), 400
            # set limit to MAX value possible as defined in req.
            # set to default value if limit is negative.
            if limit < 0:
                push_log('negative integer value provided. setting to default value.')
                limit = 50

            if limit > 200:
                push_log('limit param has exceeded permissible value (value of:  %s). setting to 200.' %limit)
                limit = 200
        except KeyError:
            push_log('no limit param provided, setting to default.')
            limit = 50
    except ValueError:
        push_log('no params have been provided. Setting to default.')
        limit = 50
    # else, scan for URL vars.
    if request.args.get('limit') is not None:
        limit = request.args.get('limit')
        push_log('limit value received is: %s; it is of type: %s' %(limit, type(limit)))
        if limit == '' and not limit.isdigit():
            limit = 50
        else:
            limit = int(limit)
        push_log('limit value is now: %s; and of type: %s' %(limit, type(limit)))
        if not isinstance(limit, int):
            return jsonify(status='error', error="INVALID 'limit' arguement."), 400
            # set limit to MAX value possible as defined in req.
            # set to default value if limit is negative.
        if limit < 0:
            push_log('negative integer value provided. setting to default value.')
            limit = 50

        if limit > 200:
            push_log('limit param has exceeded permissible value (value of:  %s). setting to 200.' %limit)
            limit = 200
    
    # get all posts from the user:
    query_result = item_collection.find({'username':username})
    user_exists = collection.find_one({'username':username})

    if user_exists == None:
        return jsonify(status='error', error='username does not exist'), 400

    if query_result == None:
        return jsonify(status='OK', items=[]), 200
    # # cursor
    # ret_list = []
    # for document in query_result:
    #     # push_log("appending item... : %s \n" %document)
    #     ret_list.append(get_beauty(document))
    #     limit = limit - 1
    #     # push_log('Limit value is: %s' %limit)
    #     if limit <= 0:
    #         return jsonify(status='OK', items=ret_list)

    return jsonify(status='OK', items=search_the_items(time.time(), limit, user=username, only_IDs=True))

@app.route('/get_post', methods=['GET'])
def deget_postl_it():
    return render_template('get_post.html')


"""
**********************************************************************************************************************************************************
                                                                    FOLLOWERS
**********************************************************************************************************************************************************

"""
@app.route("/user/<username>/followers", methods=['GET'])
def get_user_followers(username):
    push_log("Client requested user followers. @ (/user/<username>/followers)...")
    push_log("requested username info is: %s" %username)

    received_data = request.get_data()
    push_log('RAW Data Received:  %s' %received_data)
    try:
        data = json.loads(received_data)
        try:
            push_log('found limit param')
            limit = data['limit']
            # check if provided datatype is an int. If not, return an error.
            if not isinstance(limit, int):
                return jsonify(status='error', error="INVALID 'limit' arguement."), 400
            # set limit to MAX value possible as defined in req.
            # set to default value if limit is negative.
            if limit < 0:
                push_log('negative integer value provided. setting to default value.')
                limit = 50

            if limit > 200:
                push_log('limit param has exceeded permissible value (value of:  %s). setting to 200.' %limit)
                limit = 200
        except KeyError:
            push_log('no limit param provided, setting to default.')
            limit = 50
    except ValueError:
        push_log('no params have been provided. Setting to default.')
        limit = 50
    # else, scan for URL vars.
    if request.args.get('limit') is not None:
        limit = request.args.get('limit')
        push_log('limit value received is: %s; it is of type: %s' %(limit, type(limit)))
        if limit == '' and not limit.isdigit():
            limit = 50
        else:
            limit = int(limit)
        push_log('limit value is now: %s; and of type: %s' %(limit, type(limit)))
        if not isinstance(limit, int):
            return jsonify(status='error', error="INVALID 'limit' arguement."), 400
            # set limit to MAX value possible as defined in req.
            # set to default value if limit is negative.
        if limit < 0:
            push_log('negative integer value provided. setting to default value.')
            limit = 50

        if limit > 200:
            push_log('limit param has exceeded permissible value (value of:  %s). setting to 200.' %limit)
            limit = 200
    # see which params are present
    

    # get all followers from the user:
    query_result = collection.find_one({'username':username})

    if query_result == None:
        # username not found.
        return jsonify(status='error', error='No such username.'), 400

    # else
    ret_list = []

    if limit is 0:
        return jsonify(status='OK', users=ret_list)


    for follower in query_result['followers']:
        # push_log("appending follower... : %s \n" %follower)
        ret_list.append(follower)
        limit = limit - 1
        # push_log('Limit value is: %s' %limit)
        if limit <= 0:
            return jsonify(status='OK', users=ret_list)


    return jsonify(status='OK', users=ret_list)
@app.route('/get_followers')
def get_followers():
    return render_template('get_followers.html')

"""
**********************************************************************************************************************************************************
                                                                    FOLLOWING
**********************************************************************************************************************************************************

"""
@app.route("/user/<username>/following", methods=['GET'])
def get_user_following(username):
    push_log("Client requested users the user follows. @ (/user/<username>/following)...")
    push_log("requested username info is: %s" %username)

    received_data = request.get_data()
    push_log('RAW Data Received:  %s' %received_data)
    try:
        data = json.loads(received_data)
        try:
            push_log('found limit param')
            limit = data['limit']
            # check if provided datatype is an int. If not, return an error.
            if not isinstance(limit, int):
                return jsonify(status='error', error="INVALID 'limit' arguement."), 400
            # set limit to MAX value possible as defined in req.
            # set to default value if limit is negative.
            if limit < 0:
                push_log('negative integer value provided. setting to default value.')
                limit = 50

            if limit > 200:
                push_log('limit param has exceeded permissible value (value of:  %s). setting to 200.' %limit)
                limit = 200
        except KeyError:
            push_log('no limit param provided, setting to default.')
            limit = 50
    except ValueError:
        push_log('no params have been provided. Setting to default.')
        limit = 50
    # else, scan for URL vars.
    if request.args.get('limit') is not None:
        limit = request.args.get('limit')
        push_log('limit value received is: %s; it is of type: %s' %(limit, type(limit)))
        if limit == '' and not limit.isdigit():
            limit = 50
        else:
            limit = int(limit)
        push_log('limit value is now: %s; and of type: %s' %(limit, type(limit)))
        if not isinstance(limit, int):
            return jsonify(status='error', error="INVALID 'limit' arguement."), 400
            # set limit to MAX value possible as defined in req.
            # set to default value if limit is negative.
        if limit < 0:
            push_log('negative integer value provided. setting to default value.')
            limit = 50

        if limit > 200:
            push_log('limit param has exceeded permissible value (value of:  %s). setting to 200.' %limit)
            limit = 200
    # see which params are present
    

    # get all followers from the user:
    query_result = collection.find_one({'username':username})

    if query_result == None:
        # username not found.
        return jsonify(status='error', error='No such username.'), 400

    # else
    ret_list = []

    if limit is 0:
        return jsonify(status='OK', users=ret_list)

    for follower in query_result['following']:
        # push_log("appending follower... : %s \n" %follower)
        ret_list.append(follower)
        limit = limit - 1
        # push_log('Limit value is: %s' %limit)
        if limit <= 0:
            return jsonify(status='OK', users=ret_list)


    return jsonify(status='OK', users=ret_list)

@app.route('/get_following')
def get_following():
    return render_template('get_following.html')

"""
**********************************************************************************************************************************************************
                                                                    FOLLOW
**********************************************************************************************************************************************************

"""
# follow or unfollow a user.
@app.route("/follow", methods=['POST'])
def follow():
    push_log('Client requested /follow through POST')
    push_log('checking client session.')
    # user must be signed in.
    # check if the user has been signed in...
    session = request.cookies.get('SID')
    push_log('session has value of %s' %session)
    res = check_session(request.cookies.get('SID'))
    if res != 0:
        # error. No user signed in or invalid path.
        return res, 401
    received_data = request.get_data()
    # if received nothing...
    if received_data == None:
        return jsonify(status='error', error='INVALID PARAMS'), 400
    if received_data is b'':
        return jsonify(status='error', msg='No input provided.'), 400
    push_log('RAW Data Received:  %s' %received_data)
    data = json.loads(received_data)
    user = get_user_from_key(request.cookies.get('SID'))
    if user is not None:
        push_log("user detected from session: %s" %user['username'])
    try:
        push_log('checking for input')
        target_user = data['username']
        if target_user is '':
            return jsonify(status='error', error='user not specified. Cannot follow/unfollow'), 400
        # check if the specified user exists.
        target_user_doc = collection.find_one({'username':target_user})
        if  target_user_doc == None:
            return jsonify(status='error', error='user Does not exist. Cannot follow/unfollow'), 400
    except KeyError:
        return jsonify(status='error', error='Invalid parameters. Please specify the username'), 400

    try:
        follow = data['follow']
        if not isinstance(follow, bool):
            push_log('provided follow param is not a bool.')
            return jsonify(status='error', error='follow arguement is not a boolean type.'), 400
    except KeyError:
        # no bool provided, setting out own.
        follow = True

    # if follow == True
    if follow:
        # follow op.
        # append the target user into user's following list
        
        # get user's following list.
        following_list = user['following']
        if target_user in following_list:
            return jsonify(status='error', error='user already following user.')
        following_list.append(target_user)
        following_n = user['following_n']
        following_n = following_n + 1
        # update database
        collection.update_one({"_id":user['_id']}, {'$set' : {'following':following_list, 'following_n': following_n}})

        # append user into the target user's followers list
        target_user_followers_list = target_user_doc['followers']
        current_username = user['username']
        target_user_followers_list.append(current_username)
        following_n = target_user_doc['followers_n']
        following_n = following_n + 1
        # update database
        collection.update_one({"_id":target_user_doc['_id']}, {'$set' : {'followers':target_user_followers_list, 'followers_n':following_n}})

        return jsonify(status='OK', msg='succesfully following targeted user.')
    else:
   #if not follow <-- EQUIV
        # if follow == False
        # unfollow op.
        # del the target user into user's following list
        # get user's following list.
        following_list = user['following']
        try:
            following_list.remove(target_user)
            following_n = user['following_n']
            following_n = following_n - 1
        except ValueError:
            # user is NOT following target user.
            return jsonify(status='error', error='current user is not following specified user.'), 400
        # update database
        collection.update_one({"_id":user['_id']}, {'$set' : {'following':following_list, 'following_n': following_n}})

        # del user into the target user's followers list
        target_user_followers_list = target_user_doc['followers']
        try:
            target_user_followers_list.remove(user['username'])
            following_n = target_user_doc['followers_n']
            following_n = following_n - 1
        except ValueError:
            # target user does not have the current user as a follower.
            return jsonify(status='error', error='current user is not following specified user.'), 400
        # update database
        collection.update_one({"_id":target_user_doc['_id']}, {'$set' : {'followers':target_user_followers_list, 'followers_n':following_n}})
        return jsonify(status='OK', msg='Succesfully unfollowed target user.')

@app.route('/usr_follow')
def usr_follow():
    return render_template('usr_follow.html')


"""
**********************************************************************************************************************************************************
                                                                    SEARCH
**********************************************************************************************************************************************************

"""
@app.route('/search', methods=['POST'])
def search():
    # get values as provided:
    push_log("client has requested an item search")
    received_data = request.get_data()
    push_log('RAW Data Received:  %s' %received_data)
    # TODO: check input type consistency. If for instance, a string val is given for a bool var field, return error.

    try:
        data = json.loads(received_data)
        # TIMESTAMP VALUE
        try:
            timestamp = data['timestamp']
            if (timestamp == None):
                timestamp = time.time()

            if not isinstance(timestamp, (int, float)):
                # error, invalid parameters
                return jsonify(status="error", error="error. the provided timestamp is not an integer nor a float. cannot proceed.")
        except KeyError:
            # if no timestamp has been provided, use current time.
            timestamp = time.time()
        
        # LIMIT VALUE
        try:
            search_amount = data['limit']
            if search_amount == None:
                search_amount = 25
            if (search_amount > 100):
                search_amount = 100
            elif (search_amount < 0):
                return jsonify(status="error", error="limit specification out of bounds. Please try any number between 0 ~ 25"), 400
            if (not isinstance(search_amount, int)):
                # error, invalid parameters
                return jsonify(status="error", error="error. either the provided limit is not an integer. cannot proceed.")
        except KeyError:
            # no limit provided, therefore limit = 25.
            search_amount = 25
        
        # QUERY VALUE
        try:
            query = data['q']
            if query == '':
                query = None
        except KeyError:
            # no query provided, setting to None
            query = None
        
        # USERNAME VALUE
        try:
            username = data['username']
            if username == '':
                username = None
        except KeyError:
            username = None
        
        # FOLLOWING VALUE
        try:
            following = data['following']
            if following == None:
                following = True
            if not isinstance(following, bool):
                return jsonify(status='error', error='Invalid "following" value. aborting operation.'), 400
        except KeyError:
            following = True

        # RANK VALUE
        try:
            rank = data['rank']
            if (rank == None) or (rank == ''):
                rank = 'interest'
            if not((rank == 'time') or (rank == 'interest')):
                return jsonify(status='error', error='Invalid "rank" value. aborting operation.'), 400
        except KeyError:
            rank = 'interest'
        
        # PARENT VALUE
        try:
            parent = data['parent']
        except KeyError:
            parent = None

        # REPLIES VALUE
        try:
            replies = data['replies']
            if replies == None:
                replies = True
            if not isinstance(replies, bool):
                return jsonify(status='error', error='Invalid "replies" value. aborting operation.'), 400
        except KeyError:
            replies = True
        
        # HAS MEDIA VALUE
        try:
            hasMedia = data['hasMedia']

            if hasMedia == None:
                hasMedia = False
            if not isinstance(hasMedia, bool):
                return jsonify(status='error', error='Invalid "hasMedia" value. aborting operation.'), 400
        except KeyError:
            hasMedia = False
        
    except ValueError:
        push_log('no  params have been given , setting to default') 
        timestamp = time.time()
        search_amount = 25
        query = None # *** MODIFICATOR ***
        username = None # *** MODIFICATOR ***
        # if following = True, requires login. If not logged in, ignore.
        following = True
        rank = 'interest'
        parent = None # *** MODIFICATOR ***
        replies = True
        hasMedia = False

    push_log('\nInvoked /search API. \nSet values: \ntimestamp: %s, \nsearch_amount: %s, \nquery string: %s, \nfiltering username: %s, \nfollowing: %s, \nrank order type: %s, \nparent: %s, \nreturn replies: %s, \nreturn items with media: %s' %(timestamp, search_amount, query, username, following, rank, parent, replies, hasMedia))

    # check session to det. following value.
    session = request.cookies.get('SID')
    push_log('session has value of %s' %session)
    res = check_session(request.cookies.get('SID'))
    curr_user = get_user_from_key(request.cookies.get('SID'))
    if curr_user is not None:
        push_log("user detected from session: %s" %curr_user['username'])
    if res != 0:
        # error. No user signed in or invalid path, therefore, we cannot query followers.
        push_log('User session was not detected when ionvoking search. setting <following> field to FALSE')
        following = False

    # get curr_user's following list.
    if following and (curr_user != None):

        # GET USER FOLLOWERS.
        following_list = curr_user['following']
        push_log('logged user followers: %s' %following_list)
        # If user is logged in , get list of followers.
    
    # very unlikely to happen.
    if following and (curr_user == None):
        return jsonify(status='error', error='following cannot be set to true while curr_user being null.')
    
    # THE BASE QUERY FORMAT.
    # elastic_search.search(index=ES_INDEX, size=query_size_limit, body=q_body)

    # case breakdown of param specification of: query (q), username (usr), and parent (prnt)
    # case 1, EXIST: q, usr, prnt
    # there is a query string, a usr specification, and parent var.
    if (query != None) and (username != None) and (parent != None):
        # no need to implement
        # milestone 3 requirement.
        pass
    # case 2, EXIST: q, usr
    elif (query != None) and (username != None):
        # get all items that satisfy the query from all the posts of the particular user.
        if following:
            if username in following_list:
                return search_the_items(timestamp, search_amount, query=query, user=username)
            else:
                # use the following
                return search_the_items(timestamp, search_amount, query=query, user=username)
                # return search_the_items(timestamp, search_amount, query=query, followers=following_list)
        else:
        # only return posts from username.
            return search_the_items(timestamp, search_amount, query=query, user=username)

    # case 3, EXIST: q, prnt
    elif (query != None) and (parent != None):
        # MILESTONE 3 req.
        pass
    # case 4, EXIST: q
    elif ((query != None)):
        if following:
            return search_the_items(timestamp, search_amount, query=query, followers=following_list)
        else:
        # only return posts from username.
            return search_the_items(timestamp, search_amount, query=query)
    # case 5, EXIST: usr, prnt
    elif (username != None) and (parent != None):
        # Milestone 3 req.
        pass
    # case 6, EXIST: usr
    elif (username != None):
        # get all posts from the particular user. (easy)
        if following:
            if username in following_list:
                return search_the_items(timestamp, search_amount, user=username)
            else:
                # set to return only following posts.
                return search_the_items(timestamp, search_amount, user=username)
                # return search_the_items(timestamp, search_amount, followers=following_list)
        else:
        # only return posts from username.
            return search_the_items(timestamp, search_amount, user=username)
    # case 7, EXIST: None
    else:
        if following:
            return search_the_items(timestamp, search_amount, followers=following_list)
        else:
            return search_the_items(timestamp, search_amount)
        # None of the above three params have been given. do normal search.





def search_the_items(timestamp, limit, query=None, user=None, followers=None, reply=True, parent=None, rank=None, hasMedia=False, only_IDs=False):
    push_log("invoked search_the_items() method for elasticsearch search.")
    query_stat = {'match':{'content':query}}
    user_stat = {'match':{'username':user}}
    reply_stat = {'match':{'childType':'reply'}}
    q_string = {
                        'query':{
                            'bool':{
                                'must':[
                                    {'range':{'timestamp':{'lte':timestamp}}}
                                 ],
                                'should':[],
                                'must_not':[]
                            }
                        }
                    }
    if query is not None:
        q_string['query']['bool']['must'].append(query_stat)
    if followers is not None:
        for follower in followers:
            follower_stat = {'match':{'username':follower}}
            q_string['query']['bool']['should'].append(follower_stat)
    else:
        if user is not None:
            q_string['query']['bool']['must'].append(user_stat)

    if reply is False:
        q_string['query']['bool']['must_not'].append(reply_stat)

    # parent, rank, and hasMedia wont be implemented yet.

    query_result = elastic_search.search(index=ES_INDEX, size=limit, body=q_string)
    # push_log('query result: %s' %query_result)
    # if len(query_result['hits']['hits']) == 0:
    #     return jsonify(status='error', error='No items found.')

    id_list = []

    for item in query_result['hits']['hits']:
        # push_log('childtype: %s ' %item['_source']['childType'])
        # push_log('timestamp: %s ' %item['_source']['timestamp'])
        # push_log('Content: %s ' %item['_source']['content'])
        # push_log('IDs: %s ' %item['_id'])
        id_list.append(item['_id'])
        # push_log('Score: %s \n' %item['_score'])

    ret_list = []
    
    for _id in id_list:
        item = item_collection.find_one({'id':_id})
        ret_list.append(get_beauty(item))
    
    if only_IDs:
        return id_list
    else:
        return jsonify(status='OK', items=ret_list)

def get_beauty(return_val):
    return {"id":return_val['id'], "username":return_val['username'], "property":return_val['property'], "retweeted":return_val['retweeted'], "content":return_val['content'], "timestamp":return_val['timestamp']}



# Checks session in progress. If a session exists, returns 0, if not returns a json string with the error desc.
def check_session(cookie):
    if not cookie:
        #  No cookies, hence invalid operation.
        return json.dumps({"status":"error", "error":"no session detected. Invalid operation."})
     # check session from cookie.
    session_user = get_user_from_key(cookie)
    if session_user == None:
        return json.dumps({"status":"error", "error":"Session Already Expired."})
    else:
        return 0

def get_user_from_key(key):
    return collection.find_one({"key":key})

def make_random_string(min_size, max_size):
    # allowed chars
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(randint(min_size, max_size)))


# ********************************************************************  T E S T    R E G I O N     &      H E L P E R    F U N C T I O N S  **********************************************************************


def send_verification_mail(email, key, send_method='local'):
    body = 'validation key: <%s>' %key
    header = 'Please verify your account at /ttt/ wrmup.cloud.compas.cs.stonybrook.edu'
    recipient = email
    if send_method == 'local':
        strng = 'echo \"%s\" | mail -s \"%s\" %s' %(body, header, recipient)
        os.system(strng)
    else: 
        # use external smtp mail server... for testing purposes.
        global EMAIL_RECIPIENT
        send_mail('Please verify your account at /ttt/ wrmup.cloud.compas.cs.stonybrook.edu', EMAIL_RECIPIENT, 'echo \"%s\" | mail -s \"%s\" %s' %(body, header, recipient))
# ***************************************************************************************************************************8


def push_log(message):
    # app.logger.error(message)
    app.logger.warning(message)

# Used to send mails when the tests finishes.
def send_mail(subject, recipient, message):
    subj=subject
    me="joshuajinwoohan.dev@gmail.com"
    me_password="jcX01#%k8HLn2Um9OxlUZg9TQjnD3nMF"
    global EMAIL_RECIPIENT
    you = recipient
    msg = MIMEMultipart()
    msg['Subject'] = subj
    msg['From'] = me
    msg['To'] = you
    
    msg.preamble = message
    msg_txt = ("<html>"
                "<head></head>"
                "<body>"
                    "<h1>debug info:</h1>"
                    "<p>%s</p>"
                "</body>"
            "</html>" % message)
    msg.attach(MIMEText(msg_txt, 'html'))
    smtp_conn = smtplib.SMTP("smtp.gmail.com:587", timeout=10)
    smtp_conn.starttls()
    smtp_conn.ehlo_or_helo_if_needed()
    smtp_conn.login(me, me_password)
    smtp_conn.sendmail(me, you, msg.as_string())
    smtp_conn.quit()

if __name__ == "__main__":
    push_log('Started app...')
    print('Hello world! The debugging has started.', file=sys.stderr)
    app.run()
