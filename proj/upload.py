from functools import wraps
from flask import send_from_directory, render_template, request, redirect, Response, jsonify,send_file, json, current_app, session, Blueprint
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
from sqlalchemy import exc,Table,MetaData
from datetime import datetime
import pandas as pd
import numpy as np
import psycopg2, urllib, json, re, time, datetime, os, glob
import xlsxwriter, openpyxl, gc, itertools, zipfile, sh, shutil, folium
import pika
from .reformat import full_reformat

pd.set_option('display.max_columns', 18)

uploader = Blueprint("uploader", __name__)
@uploader.route('/upload', methods=['POST'])
def upload():
    try:
        print("begin upload routine")
        # delete previously uploaded files and start clean
        if len(glob.glob(os.path.join(session['new_files'], "*"))) > 0:
            sh.rm(
                glob.glob(os.path.join(session['new_files'], "*"))
            )
        if len(glob.glob(os.path.join(session['original_files'], "*"))) > 0:
            sh.rm(
                glob.glob(os.path.join(session['original_files'], "*"))
            )
        email = request.form.get("email")
        print("email")
        print(email)

        uploaded_files = request.files.getlist('files[]')
        assert len(uploaded_files) > 0, "No files found"
        uploaded_filenames = [secure_filename(x.filename) for x in uploaded_files]


        # this is used a few times throughout the script
        file_pat = re.compile(r"(.*)(?=\.)\.(.*)")

        # check to make sure they have only valid file names uploaded
        assert \
        all([
            bool(re.search(file_pat, x)) for x in uploaded_filenames
        ]), \
        "Invalid file name {}" \
        .format(
            ",".join([
                x 
                for x in uploaded_filenames
                if not bool(re.search(file_pat, x))
            ])
        )

        # This should be fine since if it gets here it passed the above assertion
        filetypes = [x.split('.')[-1].lower() for x in uploaded_filenames]
        print(filetypes)

        # Routine for checking the filetypes they submitted, since they can now submit multiple files
        allowed_filetypes = ['xls','xlsx','png','jpg']
        assert set(filetypes) - set(allowed_filetypes) == set(), \
            f"""
            This application will only accept files with the following extensions: {','.join(allowed_filetypes)}
            """
            
        
        assert len([x for x in filetypes if 'xls' in x]) < 2, \
            """
            This application has detected multiple excel files. 
            Please only submit one excel file at a time, 
            along with the corresponding images associated with the data.
            """
            
        assert len([x for x in filetypes if 'xls' in x]) != 0, "No excel file found"

            


        # Sort the uploaded files list so that the pictures go first in the loop.
        # if the excel file runs through the loop first, it never sees the photos
        # Because we are only accepting png, jpg and xls or xlsx, 
        #   the image filename extensions are always alphabetically before the excel files.
        # Therefore we sort the uploaded files list, letting the key be the extension
        print("uploading images")
        for filename, file in {k:v for k,v in zip(uploaded_filenames, uploaded_files)}.items():
            groups = re.search(file_pat,filename).groups()
            print(groups)
            
            filename = groups[0]
            extension = groups[-1]
            print(os.path.join(session['original_files'], '{}.{}'.format(filename,extension.lower()) ))
            file.save(
                os.path.join(session['original_files'], '{}.{}'.format(filename,extension.lower()))
            )

        if email != '':
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host='rabbitmq')
            )
            channel = connection.channel()

            channel.queue_declare(queue='mp_reformat')

            msgbody = json.dumps({
                'original_dir': session['original_files'],
                'new_dir': session['new_files'],
                'base_dir': session['basedir'],
                'email': email,
                'sessionid': session['sessionid']
            })

            channel.basic_publish(
                exchange = '', 
                routing_key = 'mp_reformat', 
                body = msgbody
            )
            print(f"Sent {msgbody}")
            connection.close()

            raise Exception(f"email will be sent to {email}")

        res = full_reformat(
            original_dir = session['original_files'],
            new_dir = session['new_files'],
            base_dir = session['basedir'],
            email = email,
            sessionid = session['sessionid']
        )
        
        res = json.loads(res)

        return \
        jsonify(
            message=res['message'],
            unaccounted_photos=res['unaccounted_photos'],
            missing_photos=res['missing_photos']
        )

    except Exception as e:
        print("Exception occurred")
        print(e)
        return jsonify(error="true", message = str(e))




