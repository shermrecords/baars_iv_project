import boto3
import time
import uuid
import os

# AWS Clients
s3_client = boto3.client("s3")
transcribe_client = boto3.client("transcribe")

# Config
BUCKET_NAME = "your-s3-bucket-name"


def upload_audio_to_s3(file_path, object_name=None):
    """ Uploads a local audio file to S3 """
    if object_name is None:
        object_name = os.path.basename(file_path)

    s3_client.upload_file(file_path, BUCKET_NAME, object_name)
    audio_url = f"s3://{BUCKET_NAME}/{object_name}"
    return audio_url


def start_transcription_job(audio_url):
    """ Starts an AWS Transcribe job """
    job_name = f"baars-transcribe-{uuid.uuid4()}"

    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": audio_url},
        MediaFormat="wav",
        LanguageCode="en-US"
    )
    return job_name


def wait_for_transcription(job_name):
    """ Waits for the transcription job to complete and fetches the result """
    while True:
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = response["TranscriptionJob"]["TranscriptionJobStatus"]

        if status in ["COMPLETED", "FAILED"]:
            break

        time.sleep(5)

    if status == "COMPLETED":
        transcript_url = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        return transcript_url
    else:
        raise Exception("Transcription failed")


def download_transcription(transcript_url):
    """ Downloads transcription JSON from AWS """
    import requests

    response = requests.get(transcript_url)
    return response.json()["results"]["transcripts"][0]["transcript"]


def transcribe_audio(file_path):
    """ Main function to upload and transcribe audio """
    audio_url = upload_audio_to_s3(file_path)
    job_name = start_transcription_job(audio_url)
    transcript_url = wait_for_transcription(job_name)
    return download_transcription(transcript_url)
