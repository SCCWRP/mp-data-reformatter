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
    try:
        df = pd.read_excel(
            glob.glob(os.path.join(os.getcwd(), "files", sessionid, "new", "*.xls*"))[0],
            sheet_name = "Missing Photos or Records"
        )

        missing_photos = df[~pd.isnull(df['Missing Photos'])]['Missing Photos'].tolist()

        unaccounted_photos = \
            df[
                ~pd.isnull(df['Photo with No Corresponding Record'])
            ]['Photo with No Corresponding Record'] \
            .tolist()

        # There's probably a better way of doing this
        zglob = glob.glob(os.path.join(os.getcwd(), "files", sessionid, "*.zip"))
        if len(zglob) > 0:
            zipfilename = zglob[0].split("/")[-1]
            lab = zipfilename.split("_")[0]
            matrix = zipfilename.split("_")[-1].replace(".zip","")
        else:
            raise Exception("Zip File not found")


    except Exception as e:
        missing_photos = [f"error occurred trying to get missing photo names"]
        unaccounted_photos = [f"error occurred trying to get photo names"]
        print("couldn't read in the excel file")
        print(str(e))

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