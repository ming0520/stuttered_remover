from flask import Flask, redirect, url_for, render_template,request
import speech_recognition as sr
import os
import subprocess
from shutil import move, rmtree, copyfile
import requests
import json

UPLOAD_FOLDER = '/path/to/the/uploads'
ALLOWED_EXTENSIONS = {'wav'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class Timestamp:
  def __init__(self,start = 0.0, end = 0.0, text='text'):
    self.start = start
    self.end = end
    self.text = text

@app.route('/', methods=['GET','POST'])
def index():
    transcript = "sucess"
    if request.method == "POST":
        print("FORM DATA RECEIVED")

        if "file" not in  request.files:
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            return redirect(request.url)

        if file:
            audioFile = sr.AudioFile(file)
            r = sr.Recognizer()

            with audioFile as source:
                audio = r.record(source)

            with open(f"{file.filename}", "wb") as f:
                f.write(audio.get_wav_data())

            filename = file.filename
            filename_actual = filename.split(".")[0]
            filetype = filename.split(".")[1]
            filename_audio = f'{filename_actual}_AUDIO'

            os.system(f'ffmpeg -i {filename_actual}.{filetype} -acodec pcm_s16le -ac 1 -ar 16000 -af lowpass=3000,highpass=200 {filename_audio}.wav')

            os.system(f'auto-editor {filename_audio}.wav')

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

    return render_template("index.html", transcript=transcript)

if __name__ == "__main__":
    app.run(debug=True, threaded=True)