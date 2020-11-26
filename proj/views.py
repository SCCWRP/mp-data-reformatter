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

