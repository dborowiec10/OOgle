
from flask.helpers import send_file
from app import app, auth, backend, cross_origin
import os
from flask import json, jsonify, abort, request, redirect, make_response, url_for, render_template

@auth.error_handler
def unauthorized():
    return make_response(jsonify( { 'error': 'Unauthorized access' } ), 403)

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.route("/authenticate", methods=['GET'])
@cross_origin()
def authenticate():
    return make_response(jsonify({}), 200)

@app.route("/", methods=['GET'])
@cross_origin()
def index():
    query = request.args.get("query", None)
    if query:
        result = backend.search(query)
        return render_template("index.html", 
            query=query,
            response_time=result.time,
            total=len(result.data),
            hits=len(result.data),
            start=0,
            results=result.data)
    else:
        return render_template("index.html")
    
@app.route("/addData", methods=['POST'])
@cross_origin()
def addData():
    global glob_data
    data = json.loads(request.data)
    backend.add_data(data)
    return make_response("", 200)


@app.route("/scrape", methods=['GET'])
@cross_origin()
def scrape():
    link = dict(request.args)['q']
    result = backend.scrape(link)
    return make_response(json.dumps(result, cls=backend.MyEncoder), 200)

@app.route("/static", methods=['GET'])
@cross_origin()
def staticly():
    title = dict(request.args)['t']
    sources = backend.get_sources()
    link = ""
    for tt, lnk in sources:
        if title == tt:
            link = lnk
            break
    with open(link, "rb") as static_file:
        response = make_response(static_file.read())
        response.headers.set('Content-Disposition', 'inline', filename=title + '.pdf')
        response.headers.set('Content-Type', 'application/pdf')
        return response

@app.template_filter('truncate_title')
def truncate_title(title):
    return title if len(title) <= 75 else title[:75]+"..."

@app.template_filter('truncate_description')
def truncate_description(description):
    if len(description) <= 200 :
        return description
    cut_desc = ""
    character_counter = 0
    for i, letter in enumerate(description) :
        character_counter += 1
        if character_counter > 200 :
            if letter == ' ' :
                return cut_desc+"..."
            else :
                return cut_desc.rsplit(' ',1)[0]+"..."
        cut_desc += description[i]
    return cut_desc