import os, sys, time, datetime, xlrd, urllib, json, collections
from flask import Flask, url_for, jsonify, Request, request, make_response, session
from flask_session import Session
from flask_cors import CORS, cross_origin
from sqlalchemy import create_engine
from .upload import uploader

app = Flask(__name__, static_url_path='/static')
app.debug = True # remove for production

CORS(app)
# does your application require uploaded filenames to be modified to timestamps or left as is
app.config['CORS_HEADERS'] = 'Content-Type'

app.config['MAIL_SERVER'] = '192.168.1.18'

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB limit
app.secret_key = 'any random string'
app.infile = ""

# list of database fields that should not be queried on - removed status could be a problem 9sep17 - added trawl calculated fields - removed projectcode for smc part of tbl_phab
app.system_fields = [
    "id", "objectid", "editid", "globalid", "submissionid", "gdb_geomattr_data", "shape", "record_timestamp", "timestamp","errors",
    "lastchangedate","project_code","chemistrybatchrecordid","chemistryresultsrecordid","toxbatchrecordid","toxicityresultsrecordid",
    "trawloverdistance","trawldeckdistance","trawldistance","trawlovertime","trawldecktime","trawltimetobottom","trawltime","trawldistancetonominaltarget",
    "picture_url", "coordinates", "device_type", "qcount","created_user","created_date","last_edited_user","last_edited_date","gdb_from_date","gdb_to_date",
    "gdb_archive_oid","login_email","login_agency","login_owner","login_year","login_project","lastchangedate","warnings"
]

# set the database connection string, database, and type of database we are going to point our application at
app.eng = create_engine('postgresql://sde:dinkum@192.168.1.18:5432/microplastics')
app.db = "microplastics"
app.dbtype = "postgresql"
app.status_file = ""
app.timestamp = ""
app.match = ""
app.all_dataframes = collections.OrderedDict()
app.sql_match_tables = []

app.register_blueprint(uploader)

from . import views
print("starting new microplastics application")
