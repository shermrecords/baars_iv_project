import os
import uuid
import boto3
import shutil
import time
import tempfile
import requests  # Add this import for the requests library
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json  # Add import for json

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin or specify your frontend URL here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Clients
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1"  # Update to your S3 bucket's region
)

polly_client = boto3.client("polly", region_name="us-east-1")
transcribe_client = boto3.client("transcribe", region_name="us-east-1")

# S3 Config
S3_BUCKET_NAME = "baarsdump"
S3_AUDIO_FOLDER = "audio/"

# BAARS-IV Questions
questions = [
    "How often do you feel restless or fidgety?",
    "How often do you feel impulsive or act without thinking?",
    "How often do you interrupt others when they are speaking?",
]
current_question_idx = 0

def get_transcript_url(job_name: str):
    """Retrieve the correct S3 transcript file URL."""
    bucket_name = "baarsdump"  # Replace with your actual S3 bucket
    file_path = f"{job_name}/asrOutput.json"  # The expected path in S3

    try:
        # Generate a pre-signed URL that allows temporary access to the file
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": file_path},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return url
    except Exception as e:
        print(f"Error generating pre-signed URL: {e}")
        return None  # Prevent sending "undefined" to the frontend

@app.post("/upload-response")
async def upload_response(file: UploadFile = File(...)):
    if file is None:
        print("No file received, check the frontend request.")  # Log missing file
        return {"error": "No file received, Check the frontend request."}

    try:
        # Save the file temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file_path = temp_file.name
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"File saved temporarily at: {temp_file_path}")  # Log file path

        # Upload to S3
        s3_key = f"{S3_AUDIO_FOLDER}{uuid.uuid4()}.wav"
        upload_result = upload_to_s3(temp_file_path, s3_key)
        os.remove(temp_file_path)
        print(f"File uploaded to S3 with key: {s3_key}")  # Log successful upload

        # Start transcription job
        job_name = f"transcription-{uuid.uuid4()}"
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"},
            MediaFormat="wav",
            LanguageCode="en-US",
        )
        print(f"Started transcription job with job name: {job_name}")  # Log job start

        # Return next question to the frontend
        question = get_next_question()
        return {"message": upload_result, "question": question, "job_name": job_name}

    except Exception as e:
        print(f"Failed to upload file or start transcription: {str(e)}")  # Log failure
        return {"message": f"Failed to upload file: {str(e)}"}

@app.get("/check-transcription-status/{job_name}")
async def check_transcription_status(job_name: str):
    status = "COMPLETED"  # Replace this with actual AWS Transcribe status check

    if status == "COMPLETED":
        transcript_url = get_transcript_url(job_name)
        if not transcript_url:
            return {"status": "FAILED", "error": "Transcript URL not found"}
        return {"status": "COMPLETED", "transcript_url": transcript_url}

    return {"status": "IN_PROGRESS"}

def get_next_question():
    global current_question_idx
    if current_question_idx < len(questions):
        question = questions[current_question_idx]
        current_question_idx += 1
        return question
    return "Test complete. Thank you for your responses."

def upload_to_s3(file_path: str, s3_key: str) -> str:
    try:
        s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)
        return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
    except Exception as e:
        return f"Failed to upload file to S3: {str(e)}"

def text_to_speech(text: str) -> str:
    try:
        response = polly_client.synthesize_speech(
            Text=text, OutputFormat="mp3", VoiceId="Joanna"
        )

        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_audio_path = temp_audio.name
        with open(temp_audio_path, "wb") as file:
            file.write(response["AudioStream"].read())

        s3_key = f"{S3_AUDIO_FOLDER}{uuid.uuid4()}.mp3"
        audio_url = upload_to_s3(temp_audio_path, s3_key)
        os.remove(temp_audio_path)
        return audio_url
    except Exception as e:
        return f"Error generating speech: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        with open("index.html", "r") as file:
            return file.read()
    except FileNotFoundError:
        return {"error": "index.html file not found."}

@app.get("/start-test")
async def start_test():
    question = get_next_question()
    audio_url = text_to_speech(question)
    return {"question": question, "audio": audio_url}
