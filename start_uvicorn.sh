#!/bin/bash
# Kill the process occupying port 8000
fuser -k 8000/tcp

# Start Uvicorn
poetry run uvicorn app.main:app --reload
