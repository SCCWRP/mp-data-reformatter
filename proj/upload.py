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
from .reformat import reformat

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


        
        excel_filename = glob.glob(os.path.join(session['original_files'], "*.xls*"))[0].rsplit("/", 1)[-1]
        print("filename of the excel file that was uploaded")
        print(excel_filename)

        print("copy the excel file from the old directory to the new one")
        print(
            """
            shutil.copyfile(
                os.path.join(session['original_files'], excel_filename),
                os.path.join(session['new_files'], excel_filename)
            
            )
            """
        )
        
        shutil.copyfile(
            os.path.join(session['original_files'], excel_filename),
            os.path.join(session['new_files'], excel_filename)
        )

        # Get the original sheet names of the excel file that was given
        original_sheetnames = pd.ExcelFile(os.path.join(session['original_files'], excel_filename)).sheet_names
        print("original_sheetnames")
        print(original_sheetnames)

        rawdata_tabcount = sum([bool(re.search("raw\s*data", name.lower())) for name in original_sheetnames])
        print(rawdata_tabcount)

        # Now that this code is in a try except block, we need to switch these to assert statements
        assert rawdata_tabcount != 0, \
            "Unable to determine which tab contains the raw data results"
        assert rawdata_tabcount < 2, \
            "It seems like there are two tabs that have raw data results; Unable to determine which to use"

        
        rawdata_sheetname = [name for name in original_sheetnames if bool(re.search("raw\s*data", name.lower()))][0]
        print("rawdata sheetname")
        print(rawdata_sheetname)

        original_rawdata = pd.read_excel(
            os.path.join(session['original_files'], excel_filename), 
            sheet_name = rawdata_sheetname
        )
        original_rawdata.columns = [x.lower() for x in original_rawdata.columns]
        print("original_rawdata")
        print(original_rawdata)

        # alter their data that they gave us, in ways that it should be
        # Certain columns are always uppercase text
        for col in ['labid','sampletype','sampleid']:
            original_rawdata[col] = \
                original_rawdata[col] \
                .apply(
                    lambda x: str(x).upper()
                )

        # They should not have more than one lab in their submission
        # Nor should they have more than one matrix
        assert \
            len(original_rawdata.labid.unique() == 1), \
            "There appear to be two labIDs in this one file, {}" \
            .format(','.join(original_rawdata.labid.unique()))
        session['lab'] = original_rawdata.labid.unique().tolist()[0]

        assert \
            len(original_rawdata.sampletype.unique() == 1), \
            "There appear to be two SampleTypes in this one file, {}" \
            .format(','.join(original_rawdata.sampletype.unique()))
        session['matrix'] = original_rawdata.sampletype.unique().tolist()[0]
        # above horrible code should be deleted once better way is implemented



        print("os.path.join(session['original_files'], '*.jpg')")
        print(os.path.join(session['original_files'], "*.jpg"))
        print("glob.glob(os.path.join(session['original_files'], '*.jpg'))")
        print(glob.glob(os.path.join(session['original_files'], "*.jpg")))
        uploaded_photos = [
            f.rsplit("/", 1)[-1]
            for f in 
            list(
                itertools.chain(glob.glob(os.path.join(session['original_files'], "*.jpg")), glob.glob(os.path.join(session['original_files'], "*.png")))
            )
        ]
        print("uploaded_photos")
        print(uploaded_photos)

        # doing it with p.split(".") is actually a bad way of doing it. 
        # This will prevent them from having photo names with periods in them, which technically is allowed
        # switched to using regular expressions, which in a way is also bad because the way i implement it
        # assumes they have a period in the file name
        unaccounted_photos = \
            list(
                set(re.search(file_pat, p).groups()[0] for p in uploaded_photos) - \
                set(original_rawdata.photoid.tolist())
            )
        print("unaccounted_photos")
        print(unaccounted_photos)


        # reformat the dataframe, make one for comparison and another for the final thing they will use
        comp, reformatted_data = reformat(original_rawdata)
        print("data has been reformatted")
        print("comp")
        print(comp)
        print("reformatted_data")
        print(reformatted_data)
        
        # copy images and rename them
        
        # temp dataframe that contains original filenames with extensions
        print("creating tmp")
        tmp = comp \
            .merge(
                pd.DataFrame({
                    "original_photoid": [str(p).split(".")[0] for p in uploaded_photos],
                    "original_filename": uploaded_photos
                }),
                how = 'left',
                on = 'original_photoid'
            )

        print("tmp")
        print(tmp)
        print("uploaded_photos")
        print(uploaded_photos)
        [
            os.system(
                f"""
                cp {session['original_files']}/{ids[0]} {session['new_files']}/{ids[1]}.{ids[2]};
                """
            )
            for ids in 
            zip(
                tmp.original_filename, tmp.photoid, tmp.original_filename.apply(lambda x: str(x).split('.')[-1])
            )
            if not pd.isnull(ids[0])
        ]


        ##############################################################################
        #  Routine for creating filler images or moving over the unaccounted images  #
        ##############################################################################

        missing_photos = tmp[pd.isnull(tmp.original_filename)].original_photoid.unique().tolist()
        print("missing_photos")
        print(missing_photos)

        if len(unaccounted_photos) == 0:
            # Only create filler photos if they provided all the images they could
            # Do not run this code if they have photos with no corresponding records

            # Here we create the filler images
            [ 
                os.system(f"touch {os.path.join(session['new_files'], mp)}.jpg") 
                for mp in 
                tmp[pd.isnull(tmp.original_filename)].photoid.tolist()
            ]
        else:
            # if they do have unaccounted photos, move them over
            # They will need to be warned about this though
            [
                os.system(
                    f"""
                    cp {session['original_files']}/{img} {session['new_files']}/{img};
                    """
                )
                for img in uploaded_photos
                if re.search(file_pat, img).groups()[0] in unaccounted_photos
            ]


        # finally, save the new dataframes into the new excel file
        writer = pd.ExcelWriter(os.path.join(session['new_files'], excel_filename), engine = 'openpyxl')
        writer.book = openpyxl.load_workbook(os.path.join(session['new_files'], excel_filename))

        # this dataframe will be included in the excel file to help both the user and SCCWRP
        audit = pd.DataFrame({
            "Missing Photos"          : pd.Series(missing_photos),
            "Photo with No Corresponding Record" : pd.Series(unaccounted_photos)
        })

        audit.to_excel(writer, sheet_name = "Missing Photos or Records", index = False)
        comp.to_excel(writer, sheet_name = "RawData For Comparison", index = False)
        reformatted_data.to_excel(writer, sheet_name = "new_rawdataresults", index = False)

        # Reorder the sheets in the excel file, putting lookup lists at the end
        writer.book._sheets = \
        [
            writer.book._sheets[i]
            for i in
            [
                writer.book.sheetnames.index(n)
                for n in
                list(
                    itertools.chain(
                        [x for x in writer.book.sheetnames if x[:3].lower() != 'lu_'], 
                        [x for x in writer.book.sheetnames if x[:3].lower() == 'lu_']
                    )
                )
            ]
        ]
        print("writer.book.sheetnames")
        print(writer.book.sheetnames)
        writer.save()
        writer.close()

        # move their files into a directory that is easy for them to understand
        final_dir = os.path.join(
            session['basedir'], 
            "{}_{}".format(session['lab'], session['matrix'])
        )
        print(final_dir)
        print("shutil.copytree(session['new_files'], final_dir)")
        assert final_dir.count("/") > 5, "final_dir is a too high level of a directory. Refusing to remove it"

        if os.path.exists(final_dir):
            shutil.rmtree(final_dir)
        shutil.copytree(session['new_files'], final_dir)

        z = zipfile.ZipFile("{}.zip".format(final_dir), 'w', zipfile.ZIP_DEFLATED)
        # The root directory within the ZIP file.
        rootdir = os.path.basename(final_dir)
        for dirpath, dirnames, filenames in os.walk(final_dir):
            for filename in filenames:

                # Write the file named filename to the archive,
                # giving it the archive name 'arcname'.
                filepath   = os.path.join(dirpath, filename)
                parentpath = os.path.relpath(filepath, final_dir)
                arcname    = os.path.join(rootdir, parentpath)

                z.write(filepath, arcname)
        shutil.rmtree(final_dir)

        return \
        jsonify(
            message="ok",
            unaccounted_photos=unaccounted_photos,
            missing_photos=missing_photos
        )

    except Exception as e:
        print("Exception occurred")
        print(e)
        return jsonify(error="true", message = str(e))




