from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Allow cross-origin requests from localhost:8080 (Windows side)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Only allow frontend from localhost:8080
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Serve static files (audio files, for example)
app.mount("/static", StaticFiles(directory="/home/sherm/baars_iv_project/speech_outputs"), name="static")

@app.get("/start-test")
async def start_test():
    # This route sends a sample question and audio file information
    return JSONResponse({
        "message": "Test Started",
        "question": "Are you ready to begin?",
        "audio": "speech.mp3"
    })

# Additional routes for fetching the questions (if needed)
@app.get("/next-question")
async def next_question():
    return JSONResponse({
        "question": "Do you often have trouble wrapping up the final details of a project once the challenging parts are done?",
        "audio": "speech_outputs/question_0.mp3"
    })