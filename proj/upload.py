from functools import wraps
from flask import send_from_directory, render_template, request, redirect, Response, jsonify,send_file, json, current_app, session, Blueprint
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
from sqlalchemy import exc,Table,MetaData
import urllib, json, re, time, datetime, os, glob
import pandas as pd
import numpy as np
from datetime import datetime
import psycopg2
from pandas import DataFrame
import folium
import xlsxwriter, openpyxl
import gc
import itertools

from .reformat import reformat


uploader = Blueprint("uploader", __name__)
@uploader.route('/upload', methods=['POST'])
def upload():
    uploaded_files = request.files.getlist('files[]')
    filetypes = [secure_filename(x.filename).split('.')[-1].lower() for x in uploaded_files]
    
    # Routine for checking the filetypes they submitted, since they can now submit multiple files
    allowed_filetypes = ['xls','xlsx','png','jpg']
    if set(filetypes) - set(allowed_filetypes) != set():
        badfiles = set(filetypes) - set(allowed_filetypes)
        
        return \
        jsonify(
            file_error="true",
            message=f"This application will only accept files with the following extensions: {','.join(allowed_filetypes)}"
        )
    
    if len([x for x in filetypes if 'xls' in x]) > 1:
        return \
        jsonify(
            file_error="true",
            message=f"This application has detected multiple excel files. Please only submit one excel file at a time, along with the corresponding images associated with the data."
        )
    elif len([x for x in filetypes if 'xls' in x]) == 0:
        return \
        jsonify(
            file_error="true",
            message=f"No excel file found"
        )


    # Sort the uploaded files list so that the pictures go first in the loop.
    # if the excel file runs through the loop first, it never sees the photos
    # Because we are only accepting png, jpg and xls or xlsx, 
    #   the image filename extensions are always alphabetically before the excel files.
    # Therefore we sort the uploaded files list, letting the key be the extension
    for file in uploaded_files:
        filename = secure_filename(file.filename)
        file.save(
            os.path.join(
                session['original_files'], 
                filename
            )
        )
        continue
    
    excel_filename = glob.glob(os.path.join(session['original_files'], "*.xls*"))[0].rsplit("/", 1)[-1]
    os.system(
        "cp {} {}" \
        .format(
            os.path.join(session['original_files'], excel_filename),
            os.path.join(session['new_files'], excel_filename)
        )
    )

    writer = pd.ExcelWriter(os.path.join(session['new_files'], excel_filename), engine = 'openpyxl')
    writer.book = openpyxl.load_workbook(os.path.join(session['new_files'], excel_filename))

    original_sheetnames = pd.ExcelFile(os.path.join(session['original_files'], excel_filename)).sheet_names

    rawdata_tabcount = sum([bool(re.search("raw\s*data", name.lower())) for name in original_sheetnames])
    if rawdata_tabcount == 0:
        return jsonify(file_error="true", message = "Unable to determine which tab contains the raw data results")
    elif rawdata_tabcount > 1:
        return jsonify(file_error="true", message = "It seems like there are two tabs that have raw data results; Unable to determine which to use")
    else:
        print("Ok")
    
    rawdata_sheetname = [name for name in original_sheetnames if bool(re.search("raw\s*data", name.lower()))]

    original_rawdata = pd.read_excel(
        os.path.join(session['original_files'], excel_filename), 
        sheet_name = rawdata_sheetname
    )

    uploaded_photos = [
        f.rsplit("/", 1)[-1]
        for f in 
        list(
            itertools.chain(glob.glob(os.path.join(session['original_files'], "*.jpg")), glob.glob(os.path.join(session['original_files'], "*.png")))
        )
    ]

    unaccounted_photos = set(original_rawdata.photoid.tolist()) - set(p.split(".")[0] for p in uploaded_photos) 
    if len(unaccounted_photos) > 0:
        return jsonify(file_error = "true", message="Uploaded images {} do not have corresponding records in the rawdata".format(','.join(unaccounted_photos)))

    # reformat the dataframe, make one for comparison and another for the final thing they will use
    comp, reformatted_data = reformat(original_rawdata)

    # copy images and rename them
    [
        os.system(
            f"""
            cp {session['original_files']}/{ids[0]}.jpg {session['new_files']}/{ids[1]}.jpg;
            cp {session['original_files']}/{ids[0]}.png {session['new_files']}/{ids[1]}.png;
            """
        )
        for ids in 
        zip(
            comp[comp.photoid.isin([p.split(".")[0] for p in uploaded_photos])].original_photoid, 
            comp[comp.photoid.isin([p.split(".")[0] for p in uploaded_photos])].photoid
        )
    ]
    return jsonify(message="ok")




