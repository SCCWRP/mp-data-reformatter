import pandas as pd
import glob, os, re
from werkzeug.utils import secure_filename
from datetime import datetime
import pandas as pd
import numpy as np
import json, time
import xlsxwriter, openpyxl, gc, itertools, zipfile, sh, shutil, smtplib
import pika
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import COMMASPACE, formatdate
from email import encoders

# Function to be used later in sending email
def send_mail(send_from, send_to, subject, text, filename=None, server="localhost"):
    msg = MIMEMultipart()
    
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    
    msg_content = MIMEText(text)
    msg.attach(msg_content)
    
    if filename is not None:
        attachment = open(filename,"rb")
        p = MIMEBase('application','octet-stream')
        p.set_payload((attachment).read())
        encoders.encode_base64(p)
        p.add_header('Content-Disposition','attachment; filename= %s' % filename.split("/")[-1])
        msg.attach(p)

    smtp = smtplib.SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()

def reformat(orig_df):

    grouping_columns  = ['labid','sampleid','sizefraction', 'instrumenttype']
    
    orig_df.columns = [x.lower() for x in orig_df.columns]
    
    new = orig_df \
        .groupby(
            grouping_columns
        ) \
        .apply(
            lambda x: 
            x[
                list(set(x.columns) - set(grouping_columns))
            ] \
            .reset_index()
        ) \
        .reset_index() \
        .rename(
            columns = {f'level_{len(grouping_columns)}':'particleidnumber'}
        )
    
    new['particleidnumber'] = new['particleidnumber'] + 1

    new.insert(
        new.columns.tolist().index('particleid') + 1,
        "newparticleid",
        new \
        .apply(
            lambda x:
            '{}_{}_{}_{}'.format(
                x['sampleid'],
                x['instrumenttype'],
                'above500' if x['sizefraction'] == '>500 um'
                else x['sizefraction'].replace(" um",""),
                x['particleidnumber']
            )
            , axis = 1
        )
    )
    
    newphotoids = new \
        .groupby('photoid') \
        .apply(
            lambda x:
            "{}-{}".format(min(x['particleidnumber']), max(x['particleidnumber']))           
        ) \
        .reset_index() \
        .rename(columns = {0: "particlerange"})
    
    new = pd.merge(new,newphotoids, how = 'left', on = 'photoid')
   
    new.insert(
        new.columns.tolist().index('photoid') + 1,
        'newphotoid',
        new \
        .apply(
            lambda x:
            '{}_{}_{}_{}'.format(
                x['sampleid'],
                x['instrumenttype'],
                'above500' if x['sizefraction'] == '>500 um'
                else x['sizefraction'].replace(" um",""),
                x['particlerange']
            )
            , axis = 1
        )
    )
    
    #new.drop(['particlerange','particleidnumber','particleid','photoid','index'], axis = 1, inplace = True)
    new.rename(
        columns = {
            "photoid":"original_photoid",
            "particleid":"original_particleid",
            "newphotoid":"photoid",
            "newparticleid":"particleid",

        },
        inplace = True
    )

    # comparison_df will have the old particleid and photoids side by side
    comparison_df = new[orig_df.columns.tolist()]
    comparison_df.insert(
        comparison_df.columns.tolist().index("particleid"),
        "original_particleid",
        new.original_particleid
    )
    
    comparison_df.insert(
        comparison_df.columns.tolist().index("photoid"),
        "original_photoid",
        new.original_photoid
    )

    return \
        comparison_df, \
        new.drop(["original_photoid","original_particleid"], axis = 1)




def full_reformat(original_dir, new_dir, base_dir, email, sessionid):
    '''
    original_dir is just the directory that keeps the user's original files
    new_dir is the one they will be transferred to
    base_dir is the folder that contains both of those folders. The zip file will be stored there
    '''
    # What does this thing need from upload.py?
    # non empty original directory session['original_files']
    # new directory session['new_files']
    # base directory session['basedir']
    # an email address to send stuff to
    # probably the same libraries that are loaded in upload.py
    # email libraries
    # the email function
    # connection to the postfix mail server running on the host machine
    # connection to microplastics docker network, 
    #   and that reformatter and rabbitmq containers are also connected to that network
    try:
        # this is used a few times throughout the script
        file_pat = re.compile(r"(.*)(?=\.)\.(.*)")

        excel_filename = glob.glob(os.path.join(original_dir, "*.xls*"))[0].rsplit("/", 1)[-1]
        print("filename of the excel file that was uploaded")
        print(excel_filename)

        print("copy the excel file from the old directory to the new one")
        print(
            """
            shutil.copyfile(
                os.path.join(original_dir, excel_filename),
                os.path.join(new_dir, excel_filename)
            
            )
            """
        )
        
        shutil.copyfile(
            os.path.join(original_dir, excel_filename),
            os.path.join(new_dir, excel_filename)
        )

        # Get the original sheet names of the excel file that was given
        original_sheetnames = pd.ExcelFile(os.path.join(original_dir, excel_filename)).sheet_names
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
            os.path.join(original_dir, excel_filename), 
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
        lab = original_rawdata.labid.unique().tolist()[0]

        assert \
            len(original_rawdata.sampletype.unique() == 1), \
            "There appear to be two SampleTypes in this one file, {}" \
            .format(','.join(original_rawdata.sampletype.unique()))
        matrix = original_rawdata.sampletype.unique().tolist()[0]
        # above horrible code should be deleted once better way is implemented



        print("os.path.join(original_dir, '*.jpg')")
        print(os.path.join(original_dir, "*.jpg"))
        print("glob.glob(os.path.join(original_dir, '*.jpg'))")
        print(glob.glob(os.path.join(original_dir, "*.jpg")))
        uploaded_photos = [
            f.rsplit("/", 1)[-1]
            for f in 
            list(
                itertools.chain(glob.glob(os.path.join(original_dir, "*.jpg")), glob.glob(os.path.join(original_dir, "*.png")))
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
                cp {original_dir}/{ids[0]} {new_dir}/{ids[1]}.{ids[2]};
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
                os.system(f"touch {os.path.join(new_dir, mp)}.jpg") 
                for mp in 
                tmp[pd.isnull(tmp.original_filename)].photoid.tolist()
            ]
        else:
            # if they do have unaccounted photos, move them over
            # They will need to be warned about this though
            [
                os.system(
                    f"""
                    cp {original_dir}/{img} {new_dir}/{img};
                    """
                )
                for img in uploaded_photos
                if re.search(file_pat, img).groups()[0] in unaccounted_photos
            ]


        # finally, save the new dataframes into the new excel file
        writer = pd.ExcelWriter(os.path.join(new_dir, excel_filename), engine = 'openpyxl')
        writer.book = openpyxl.load_workbook(os.path.join(new_dir, excel_filename))

        # this dataframe will be included in the excel file to help both the user and SCCWRP
        audit = pd.DataFrame({
            "Missing Photos"                     : pd.Series(missing_photos),
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
            base_dir, 
            "{}_{}".format(lab, matrix)
        )
        print(final_dir)
        print("shutil.copytree(new_dir, final_dir)")
        assert final_dir.count("/") > 5, "final_dir is a too high level of a directory. Refusing to remove it"

        if os.path.exists(final_dir):
            shutil.rmtree(final_dir)
        shutil.copytree(new_dir, final_dir)

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

        dl_link = f"https://mpchecker.sccwrp.org/reformat/{sessionid}"
        print("dl_link")
        print(dl_link)
        
        if email:
            send_mail(
                "admin@mpchecker.sccwrp.org",
                [email, "robertb@sccwrp.org"],
                "Microplastics - Reformatted Data",
                f"Your reformatted data and report are available here: {dl_link}",
                server = '192.168.1.18'
            )

        return json.dumps(
            {
                "message":"ok",
                "unaccounted_photos": unaccounted_photos,
                "missing_photos": missing_photos

            }
        )

    except Exception as e:
        print("Exception occurred")
        print(e)
        return json.dumps({"error":"true", "message":str(e)})