import gradio as gr
import os
import azure.cognitiveservices.speech as speechsdk
from moviepy.editor import VideoFileClip, concatenate_videoclips
from spellchecker import SpellChecker
import stanza
import requests






# Step 1: Set up Kaggle API credentials
# Define Kaggle credentials as strings
kaggle_username = "bhavukagrawal"
kaggle_key = "86c30a58809bcf433c82998a35181663"



os.environ['KAGGLE_USERNAME'] =(kaggle_username)  # Get username from environment variable
os.environ['KAGGLE_KEY'] =(kaggle_key)  # Get API key from environment variable

# Step 2: Specify the dataset identifier
dataset = '/Users/bhavukagrawal/sih app/datasets'  # Replace with the Kaggle dataset identifier

#)

# Step 4: List downloaded files
print("Downloaded files:", os.listdir('datasets'))


os.environ["AZURE_SPEECH_KEY"] = "2ff3a4a0470149f8b1898c0036eea110"
os.environ["AZURE_SPEECH_REGION"] = "eastasia"

os.environ["AZURE_TRANSLATOR_KEY"] = "1b2924ec518c471e98dfe473aaba0adb"
os.environ["AZURE_TRANSLATOR_ENDPOINT"] = "https://api.cognitive.microsofttranslator.com/"



# Initialize spell checker and stanza
spell = SpellChecker()
stanza.download('en')
nlp = stanza.Pipeline('en')

# Function to transcribe Gujarati audio to text using Azure Cognitive Services
def transcribe_audio_to_text(audio_path):
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_recognition_language = "gu-IN"

    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    else:
        return None

# Function to translate text using Azure Translator
def translate_text(text, to_lang="en"):
    subscription_key = os.getenv("AZURE_TRANSLATOR_KEY")
    endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT") + "/translate"

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Ocp-Apim-Subscription-Region': os.getenv("AZURE_SPEECH_REGION"),
        'Content-type': 'application/json'
    }

    params = {
        'api-version': '3.0',
        'from': 'gu',
        'to': [to_lang]
    }

    body = [{'text': text}]

    response = requests.post(endpoint, headers=headers, params=params, json=body)
    response = response.json()

    return response[0]['translations'][0]['text']

# Function to parse text using Stanza
def parse(text):
    doc = nlp(text)
    result = [(word.text.lower(), word.lemma.lower()) for sentence in doc.sentences for word in sentence.words]
    return result

# Function to generate video from parsed words
def generate_video(word_list):
    #folder = os.getcwd()
    filePrefix =  "datasets"
    files = [filePrefix + "/" + word + ".mp4" for word in word_list]
    existing_files = [file for file in files if os.path.exists(file)]

    if not existing_files:
        raise FileNotFoundError("No video clips found for the given words.")

    try:
        clips = [VideoFileClip(file) for file in existing_files]
        final_clip = concatenate_videoclips(clips)
        output_path = 'output.mp4'
        final_clip.write_videofile(output_path)
    except Exception as e:
        return f"Error during video concatenation: {e}"

    return output_path

# Function to process the audio or video file and generate a sign language video
def process_audio(file_path):
    try:
        # Check if the file is a video
        if file_path.endswith('.mp4'):
            video = VideoFileClip(file_path)
            audio_path = "extracted_audio.wav"
            video.audio.write_audiofile(audio_path)
        else:
            audio_path = file_path

        gujarati_text = transcribe_audio_to_text(audio_path)
        if not gujarati_text:
            return None, "", "", "Error: Could not transcribe audio."

        english_text = translate_text(gujarati_text)
        if not english_text:
            return None, gujarati_text, "", "Error: Could not translate text."

        parsed = parse(english_text)
        word_list = [word[1] for word in parsed]
        video_path = generate_video(word_list)

        if not video_path:
            return None, gujarati_text, english_text, "Error: No matching video clips found."

        return video_path, gujarati_text, english_text, ""  # Return video path, Gujarati text, English text on success
    except Exception as e:
        return None, "", "", f"Error processing file: {e}"  # Return error message

# Gradio Interface Setup
iface = gr.Interface(
    fn=process_audio,
    inputs=gr.Audio(type="filepath"),
    outputs=[
        gr.Video(label="Generated Sign Language Video"),
        gr.Textbox(label="Gujarati Transcribed Text"),
        gr.Textbox(label="English Translated Text"),
        gr.Textbox(label="Error Message")
    ],
    title="Gujarati Audio/Video to Sign Language",
    description="Upload a Gujarati audio or video file to receive a corresponding sign language video, along with the Gujarati transcription and English translation."
)

# Launch the interface with sharing and debugging enabled
iface.launch(share=True, debug=True)
