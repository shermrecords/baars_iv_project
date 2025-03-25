import os
import uuid
import boto3
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import tempfile
import shutil
from time import sleep

app = FastAPI()

# Set up the S3 client with your specific AWS profile (make sure to have configured your AWS CLI)
s3_client = boto3.client('s3', region_name='us-west-2')
polly_client = boto3.client('polly', region_name='us-west-2')  # Polly client for TTS

# Define your S3 bucket name
S3_BUCKET_NAME = "baarsdump"
S3_AUDIO_FOLDER = "audio/"

# List of questions for the BAARS-IV test
questions = [
    "How often do you feel restless or fidgety?",
    "How often do you feel impulsive or act without thinking?",
    "How often do you interrupt others when they are speaking?",
    # Add more questions here as per the BAARS-IV test
]

current_question_idx = 0

# Function to get the next question
def get_next_question():
    global current_question_idx
    if current_question_idx < len(questions):
        question = questions[current_question_idx]
        current_question_idx += 1
        return question
    else:
        return "Test complete. Thank you for your responses."

# Create an endpoint to serve the HTML page
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r") as file:
        return file.read()

# Create an endpoint for starting the test
@app.get("/start-test")
async def start_test():
    question = get_next_question()

    # Convert the question text to speech using AWS Polly
    audio_url = text_to_speech(question)
    
    # Log the audio URL to confirm it's being returned
    print(f"Audio URL: {audio_url}")

    return {"question": question, "audio": audio_url}

# Create an endpoint for the user to upload their recorded response
@app.post("/upload-response")
async def upload_response(file: UploadFile = File(...)):
    try:
        # Create a temporary file to store the uploaded file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file_path = temp_file.name
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Generate a unique key for the uploaded file
        unique_key = f"{S3_AUDIO_FOLDER}{str(uuid.uuid4())}.wav"
        
        # Upload the file to S3
        upload_result = upload_to_s3(temp_file_path, unique_key)
        
        # Clean up the temporary file
        os.remove(temp_file_path)
        
        # Get next question
        question = get_next_question()
        
        return {"message": upload_result, "question": question}
    
    except Exception as e:
        return {"message": f"Failed to upload file: {str(e)}"}

# Function to upload to S3
def upload_to_s3(file_path: str, s3_key: str):
    try:
        # Upload the file to S3 bucket
        s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)
        return f"File uploaded successfully to s3://{S3_BUCKET_NAME}/{s3_key}"
    except Exception as e:
        return f"Failed to upload file to S3: {str(e)}"

# Function to convert text to speech using AWS Polly
def text_to_speech(text: str) -> str:
    try:
        # Call Polly to convert text to speech
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",  # You can choose 'mp3' or 'ogg_vorbis' format
            VoiceId="Joanna"  # Choose a voice from Polly (Joanna is a popular one)
        )

        # Save the audio to a temporary file
        audio_filename = f"audio_{uuid.uuid4()}.mp3"
        audio_path = os.path.join("/tmp", audio_filename)

        with open(audio_path, "wb") as file:
            file.write(response["AudioStream"].read())

        # Upload the audio file to S3
        s3_key = f"{S3_AUDIO_FOLDER}{audio_filename}"
        s3_client.upload_file(audio_path, S3_BUCKET_NAME, s3_key)

        # Clean up the temporary file
        os.remove(audio_path)

        # Return the S3 URL for the audio
        audio_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        return audio_url

    except Exception as e:
        return f"Error generating speech: {str(e)}"