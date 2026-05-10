from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agents import run_pipeline
from models import PipelineResponse
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI(title="Misinformation Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"

class FactRequest(BaseModel):
    fact: str

@app.get("/")
def root():
    return {"message": "Misinformation Pipeline API is running"}

@app.post("/api/analyze", response_model=PipelineResponse)
async def analyze(request: FactRequest):
    if not request.fact.strip():
        raise HTTPException(status_code=400, detail="Fact cannot be empty")
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set. Add it to your environment.")
    try:
        result = await run_pipeline(request.fact, "groq", GROQ_API_KEY, GROQ_MODEL)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))