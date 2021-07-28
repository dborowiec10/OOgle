from flask import Flask
from flask_httpauth import HTTPBasicAuth
from flask_cors import CORS, cross_origin
app = Flask(__name__)
cors = CORS(app, resource={
    r"/*":{
        "origins":"*"
    }
})
app.config['CORS_HEADERS'] = 'Content-Type'
auth = HTTPBasicAuth()

from app import views
from app import backend
