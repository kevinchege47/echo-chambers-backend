from pydantic import BaseModel
from typing import Optional

class FactRequest(BaseModel):
    fact: str
    provider: str = "groq"
    api_key: str
    model: Optional[str] = None

class AgentResult(BaseModel):
    agent_id: str
    agent_name: str
    agent_emoji: str
    role_description: str
    original_text: str
    rewritten_text: str
    distortion_score: float
    distortion_tactics: list[str]

class PipelineResponse(BaseModel):
    original_fact: str
    agents: list[AgentResult]
    total_distortion: float
    final_vs_original_score: float
