from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import FactRequest, PipelineResponse
from agents import run_pipeline

app = FastAPI(title="Misinformation Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Misinformation Pipeline API is running"}

@app.post("/api/analyze", response_model=PipelineResponse)
async def analyze(request: FactRequest):
    if not request.fact.strip():
        raise HTTPException(status_code=400, detail="Fact cannot be empty")
    try:
        result = await run_pipeline(request.fact, request.provider, request.api_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/providers")
def get_providers():
    return {
        "providers": [
            {
                "id": "groq",
                "name": "Groq (Free)",
                "models": [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "mixtral-8x7b-32768",
                    "gemma2-9b-it"
                ],
                "api_key_url": "https://console.groq.com/keys"
            },
            {
                "id": "claude",
                "name": "Anthropic Claude",
                "models": [
                    "claude-haiku-4-5-20251001",
                    "claude-sonnet-4-6"
                ],
                "api_key_url": "https://console.anthropic.com"
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "models": [
                    "gpt-4o-mini",
                    "gpt-4o"
                ],
                "api_key_url": "https://platform.openai.com/api-keys"
            }
        ]
    }
