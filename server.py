from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scripts.fast_video_analysis import FastVideoAnalyzer
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/analyze")
async def analyze(url: str):
    try:
        analyzer = FastVideoAnalyzer()
        result = await analyzer.analyze_video(url)
        return result
    except Exception as e:
        return {"error": str(e)}