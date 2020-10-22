import os
from flask import Flask, flash, request, redirect, url_for,render_template, send_file
from werkzeug.utils import secure_filename
import subprocess
from shutil import move, rmtree, copyfile
import requests
import json

class Timestamp:
  def __init__(self,start = 0.0, end = 0.0, text='text'):
    self.start = start
    self.end = end
    self.text = text

UPLOAD_FOLDER = './'
ALLOWED_EXTENSIONS = {'wav', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''
from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    filename = filename
    filename_actual = filename.split(".")[0]
    filetype = filename.split(".")[1]
    filename_audio = f'{filename_actual}_AUDIO'

    os.system(f'ffmpeg -y -i {filename_actual}.{filetype} -acodec pcm_s16le -ac 1 -ar 16000 -af lowpass=3000,highpass=200 {filename_audio}.wav')
    # subprocess.call(f'ffmpeg -y -i {filename_actual}.{filetype} -acodec pcm_s16le -ac 1 -ar 16000 -af lowpass=3000,highpass=200 {filename_audio}.wav', shell=True)

    os.system(f'auto-editor {filename_audio}.wav')
    # subprocess.call(f'auto-editor {filename_audio}.wav', shell=True)
    headers = {
        'Content-Type': 'audio/wav',
    }

    params = (
        ('model', 'en-US_BroadbandModel'),
        ('timestamps', 'true'),
        ('max_alternatives', '1'),
    )

    data = open(f'{filename_audio}_ALTERED.wav', 'rb').read()
    response = requests.post('https://api.jp-tok.speech-to-text.watson.cloud.ibm.com/instances/69250ebc-5a34-42a0-9096-ab9b382e2c25/v1/recognize', 
                            headers=headers, params=params, data=data, auth=('apikey', 'P75zKPwgFW2iwgbKS2GGApeuT84TymaJuFhFF88mYrPN'))

    watson = response.json()
    timestamps = watson['results'][0]['alternatives'][0]['timestamps']
    
    ts_list = []
    for timestamp in timestamps:
        if (timestamp[0]!="%HESITATION"):
            ts_list.append(Timestamp(timestamp[1],timestamp[2],timestamp[0]))

    between = []
    for ts in ts_list:
        between.append(f'between(t,{ts.start},{ts.end})')

    betweens = '+'.join(between)
    slt = '\"select=\'' + betweens + '\'' + ',setpts=N/FRAME_RATE/TB\"'
    aslt = '\"aselect=\'' + betweens + '\'' + ',asetpts=N/SR/TB\"'
    sltFilter = ['ffmpeg','-y','-i',f'{filename_audio}_ALTERED.wav', '-vf', f'{slt}','-af', f'{aslt}', f'{filename_actual}_FILTERED.wav']
    total_string = ' '.join(sltFilter)
    os.system(total_string)
    print("Done!")
    filepath=""
    filename = f'{filename_actual}_FILTERED.wav'
    # return send_file(os.path.join(filepath, filename), as_attachment=True)
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                                filename)
if __name__ == "__main__":
    app.run(debug=True, threaded=True)
    #app.run(host=127.0.0.1, port=8080,debug=True)