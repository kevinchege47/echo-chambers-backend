import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from agents import run_pipeline
from models import PipelineResponse

load_dotenv()
IS_PROD = os.getenv("ENV") == "production"
app = FastAPI(
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json"
)
# Trust Nginx forwarded headers
app.add_middleware(ProxyHeadersMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://www.yourdomain.com",
        "http://localhost:4200"   # local development only
    ],
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