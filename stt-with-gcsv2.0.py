import speech_recognition as sr
from os import path
from pydub import AudioSegment
from pydub.generators import Sine
import os
import mimetypes
import pathlib # to manage files, merge directories
from google.cloud import speech_v1p1beta1 as speech #google speech
from google.cloud import storage # storage module, google storage 
from better_profanity import profanity #will be used for profanity detection
# profanity.add_censor_words(custom_words= ['gago','gagu','nakakagago','napakagago','bobo','bubu','bobu','tanga','pakyu','fuck','putangina','tangina','putang','putanginang','tang','puking'])
from pydub.playback import play
import time

list = []
with open("mura.txt","r") as f:
    for word in f:
        list.append(word.rstrip("\n"))
profanity.add_censor_words(custom_words=list)

class Stopwatch:
    def __init__(self):
        self.start_time = time.time()
        self.lap_times = []
    
    def lap(self):
        current_time = time.time()
        lap_time = current_time - self.start_time
        self.lap_times.append(lap_time)
        self.start_time = current_time
    
    def stop(self):
        current_time = time.time()
        total_time = current_time - self.start_time
        self.lap_times.append(total_time)
        print(f'Total time: {total_time:.2f} seconds')
        for i, lap_time in enumerate(self.lap_times):
            print(f'Lap {i+1}: {lap_time:.2f} seconds')

stopwatch = Stopwatch()

# Google Authenticator
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'C://Users//Nicole//Desktop//BleepBot//bleepbot-43d63b6db2c7.json'
speech_client = speech.SpeechClient()

############# start the stopwatch FROM MIC (LAP1)
stopwatch.lap()
#start transcribing from microphone
r = sr.Recognizer()
with sr.Microphone() as source:
    r.adjust_for_ambient_noise(source)
    print("Start ")
    audio = r.listen(source)
# Combine the two audio files
    print("recognizing now... ")
    with open("C://Users//Nicole//Desktop//BleepBot//saved audio//newaudionic.wav", "wb") as f: # cache the transcribed audio (don't know yet paano directly sa Google cloud storage)
        f.write(audio.get_wav_data())

############# start the stopwatch AFTER MIC ###### TIME FOR HOW LONG IS THE AUDIO FILE (LAP2)
stopwatch.lap()

# Google Cloud BUCKET
STORAGE_CLASSES = ('STANDARD', 'NEARLINE', 'COLDLINE','ARCHIVE')

class GCStorage:
    def __init__(self, storage_client):
        self.client = storage_client
    
    # create the bucket
    def create_bucket(self, bucket_name, storage_class, bucket_location='ASIA-SOUTHEAST1'):
        bucket = self.client.bucket(bucket_name)
        bucket.storage_class = storage_class
        return self.client.create_bucket(bucket, bucket_location)
    
    # check the bucket existance
    def get_bucket(self, bucket_name):
        return self.client.get_bucket(bucket_name)

    # list of the bucket
    def list_buckets(self):
        buckets = self.client.list_buckets()
        return [bucket.name for bucket in buckets]
    
    def upload_file(self, bucket, blob_destination, file_path):
        file_type = file_path.split('.')[-1]
        if file_type == 'wav':
            content_type ='recordedaudio/wav'
        else:
            content_type = mimetypes.guess_type(file_path)[0]
        blob = bucket.blob(blob_destination)
        blob.upload_from_filename(file_path, content_type=content_type)
        return blob

# step 1
working_dir = pathlib.Path.cwd()
files_folder = working_dir.joinpath('C://Users//Nicole//Desktop//BleepBot//saved audio')
bucket_name = 'gcs_audio_files'

# step 2
storage_client = storage.Client()
gcs = GCStorage(storage_client)

# step 3 create the bucket
if not bucket_name in gcs.list_buckets(): # to check if the buckets exists
    bucket_gcs = gcs.create_bucket('gcs_audio_files', STORAGE_CLASSES[0])
else:
    bucket_gcs = gcs.get_bucket(bucket_name)

# step 4 upload files in GCS # need to do this automatically everytime there is a wav file detected
for file_path in files_folder.glob('*'):
    # use full file name
    gcs.upload_file(bucket_gcs, file_path.name, str(file_path))

################## take a lap TO GCS  ###### TIME FOR HOW LONG IS THE GCS (LAP3)
stopwatch.lap()

print("about to transcribe... ")
# using Google Cloud STT to transcribe audio file
media_uri = 'gs://gcs_audio_files/newaudionic.wav'
long_audi_wav = speech.RecognitionAudio(uri=media_uri)

config_wav_enhanced = speech.RecognitionConfig(
    sample_rate_hertz=44100,
    enable_automatic_punctuation=True,
    enable_word_time_offsets=True,
    language_code='fil-PH',
    use_enhanced=True
)
config_wav = speech.RecognitionConfig(
    sample_rate_hertz=44100,
    enable_automatic_punctuation=True,
    enable_word_time_offsets=True,
    language_code='fil-PH',
    use_enhanced=True
)

operation = speech_client.long_running_recognize(
    config = config_wav,
    audio=long_audi_wav
)

response = operation.result(timeout=90)
###################### take a lap TO GSTT ###### TIME FOR HOW LONG IS THE GSTT (LAP4)
stopwatch.lap()
# print("How long is the GSTT:", stopwatch.lap_time)

# Transcript tree
# print(response)


def beeper_filtering(z,sine_wave,a,b):
    sine_segment = sine_wave.to_audio_segment(duration = (b - a) * 1100)

    # filters = {
    #             'Beep': lambda x: Sine.to_audio_segment(b - a * 1100)
    #           }

    start = 0
    first_second = z[start:(a) * 1100] #gets 1st clip
    start = b * 1100
    slice = z[start:] #gets 2nd clip

    combined_sounds = first_second + sine_segment + slice

    return combined_sounds
    
# timestamps per word
for result in response.results:
        alternative = result.alternatives[0]
        print("Transcript: {}".format(alternative.transcript))
        print("Confidence: {}".format(alternative.confidence))
        z = AudioSegment.from_wav("C://Users//Nicole//Desktop//BleepBot//saved audio//newaudionic.wav")
        #another possible option for bleep
        #moo = AudioSegment.from_wav("C://Adrian//Bleepbot//videoplayback.wav")
        frequency = 2000
        sine_wave = Sine(frequency, sample_rate=44100, bit_depth=16)
        #play(z)
        for word_info in alternative.words:
            
            og_word = word_info.word
            word = profanity.censor(word_info.word)
            mura = profanity.contains_profanity(og_word)
            start_time = word_info.start_time
            end_time = word_info.end_time

            # Print details    
            # print(f"Word: {word}, class:{mura}, start_time: {start_time.total_seconds()}, end_time: {end_time.total_seconds()}")

            if (mura == True):
                    print(word)
                    words = word.split()
                    pwords = [words]
                    start_time = (word_info.start_time)
                    end_time = word_info.end_time
                    a = start_time.total_seconds()
                    b = end_time.total_seconds()
                    z = beeper_filtering(z,sine_wave,a,b)

            else:
                    print(" ")

        ################# take a lap TO OUTPUT ###### TIME FOR HOW LONG IS THE BLEEPING (LAP5)
        stopwatch.lap()
        #playing the final output            
        play(z)

        # stop the stopwatch and print the lap times LAP 6 HOW LONG FILTERED AUDIO
        stopwatch.stop()
