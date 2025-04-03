import os
import uuid
import boto3
import shutil
import time
import tempfile
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

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
s3_client = boto3.client("s3", region_name="us-east-1")
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

def get_transcription_text(job_name):
    while True:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = response["TranscriptionJob"]["TranscriptionJobStatus"]

        if status == "COMPLETED":
            transcript_url = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
            return transcript_url  # The frontend should fetch this URL
        elif status == "FAILED":
            return {"error": "Transcription failed"}
        
        time.sleep(5)  # Wait and check again




@app.post("/upload-response")
async def upload_response(file: UploadFile = File(...)):
    if file is None:
        return {"error": "No file received, Check the frontend request."}

    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file_path = temp_file.name
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        s3_key = f"{S3_AUDIO_FOLDER}{uuid.uuid4()}.wav"
        upload_result = upload_to_s3(temp_file_path, s3_key)
        os.remove(temp_file_path)

        job_name = f"transcription-{uuid.uuid4()}"

        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"},
            MediaFormat="wav",
            LanguageCode="en-US",
        )

        question = get_next_question()
        return {"message": upload_result, "question": question, "job_name": job_name}

    except Exception as e:
        return {"message": f"Failed to upload file: {str(e)}"}

@app.get("/transcription-status/{job_name}")
async def transcription_status(job_name: str):
    try:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = response["TranscriptionJob"]["TranscriptionJobStatus"]

        if status == "COMPLETED":
            transcript_uri = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
            return {"status": "COMPLETED", "transcript_url": transcript_uri}
        elif status == "FAILED":
            return {"status": "FAILED"}
        return {"status": "IN_PROGRESS"}

    except transcribe_client.exceptions.BadRequestException:
        return {"error": "Job not found. Job may have expired or was never created."}

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
    with open("index.html", "r") as file:
        return file.read()

@app.get("/start-test")
async def start_test():
    question = get_next_question()
    audio_url = text_to_speech(question)
    return {"question": question, "audio": audio_url}



