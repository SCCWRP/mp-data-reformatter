from proj import app
from functools import wraps
from flask import send_from_directory, render_template, request, redirect, Response, jsonify,send_file, json, current_app, session
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
from sqlalchemy import exc,Table,MetaData
import urllib, json, re, time, datetime, os
import pandas as pd
import numpy as np
from datetime import datetime
import psycopg2
from pandas import DataFrame
import folium
import xlsxwriter
import gc
import glob, sh

@app.route('/')
def index():
    print(session.get('sessionid'))
    if session.get('sessionid') is None:
        session['sessionid'] = str(int(time.time()))

        session['basedir'] = os.path.join(os.getcwd(), "files", session['sessionid'])
        session['original_files'] = os.path.join(os.getcwd(), "files", session['sessionid'], "original")
        session['new_files'] = os.path.join(os.getcwd(), "files", session['sessionid'], "new")

        os.system("mkdir -p {}".format(session['basedir']))
        os.system("mkdir -p {}".format(session['original_files']))
        os.system("mkdir -p {}".format(session['new_files']))

    return render_template("index.html", sessionid=session['sessionid'])

@app.route('/reformatted')
def reformatted():
    sessionid = request.args.get("sessionid")
    lab = request.args.get("lab")
    matrix = request.args.get("matrix")
    if sessionid and lab and matrix:
        z = os.path.join( os.getcwd(), "files", sessionid, f"{lab}_{matrix}.zip") 
       
        if os.path.exists(z):
            return send_file(
                z, as_attachment=True, attachment_filename=f"{lab}_{matrix}.zip"
            )
        else:
            return "reformatted zip file not found on the server"

    if session.get("new_files"):
        z = os.path.join(
            session['basedir'], 
            "{}_{}.zip".format(session['lab'], session['matrix'])
        )
                
        if os.path.exists(z):
            return send_file(
                z, as_attachment=True, attachment_filename="{}_{}.zip".format(session['lab'], session['matrix'])
            )
        else:
            return "reformatted zip file not found on the server"
    else:
        return "nothing has been uploaded yet"


@app.route('/status')
def status():
    if session.get("original_files") and session.get("new_files"):
        if len(glob.glob(os.path.join(session['original_files'], "*"))) > 0:
            if len(glob.glob(os.path.join(session['new_files'], "*"))) > 0:
                return jsonify(message="files processed")
            else:
                return jsonify(message="files received")
        return jsonify(message="nothing")
    else:
        return jsonify(message="Server received this request unexpectedly")

@app.route('/clear')
def clear():
    if session.get("new_files") and session.get("original_files"):
        # start fresh
        if len(glob.glob(os.path.join(session['new_files'], "*"))) > 0:
            sh.rm(
                glob.glob(os.path.join(session['new_files'], "*"))
            )
        if len(glob.glob(os.path.join(session['original_files'], "*"))) > 0:
            sh.rm(
                glob.glob(os.path.join(session['original_files'], "*"))
            )
        return jsonify(message="ok")
    else:
        return jsonify(message="Unexpected request received")

@app.route('/<sessionid>')
def report(sessionid):
    jsonpath = os.path.join(os.getcwd(), "files", sessionid, f"{sessionid}.json")
    if os.path.exists(jsonpath):
        data = json.loads(open(jsonpath, 'r').read())
    else:
        return "json file with relevant data was not found."

    lab = data.get('lab')
    matrix = data.get('matrix')
    missing_photos = data.get('missing_photos')
    unaccounted_photos = data.get('unaccounted_photos')

    if sessionid and lab and matrix:
        return render_template(
            "report.html", 
            sessionid=sessionid, 
            lab=lab, 
            matrix=matrix, 
            missing_photos=missing_photos,
            unaccounted_photos=unaccounted_photos
        )
    else:
        return "unexpected request"