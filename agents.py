import json
import re
import httpx
from models import AgentResult, PipelineResponse

# ---------------------------------------------------------------------------
# GUARDRAILS
# ---------------------------------------------------------------------------

GUARDRAIL_PROMPT = """You are a content safety filter for an educational misinformation simulator.

Your job is to decide if the given input is safe to process.

REJECT if the input:
- Targets a real, named living person to fabricate quotes or scandals about them
- Is designed to create defamatory content about a specific individual
- Contains hate speech, slurs, or content targeting a group based on race, religion, gender, or sexuality
- Asks to simulate misinformation about a real ongoing crisis in a way that could cause real harm (e.g. active disaster, medical emergency)
- Is sexually explicit or involves minors
- Is designed to incite violence or radicalize

ALLOW if the input:
- Is a generic news-style fact (health, science, politics, economics, sports, food, etc.)
- References real events or studies in a general, non-targeted way
- Is clearly hypothetical or fictional
- Names public figures only in the context of their public roles (e.g. a policy decision, not fabricated personal scandal)

Return ONLY a JSON object:
{
  "safe": true or false,
  "reason": "one sentence explanation if rejected, empty string if safe"
}"""


FACT_QUALITY_PROMPT = """You are a fact quality checker for an educational misinformation simulator.

The user has submitted text to run through a media distortion pipeline.
Your job is to check if it is suitable — meaning it resembles a real fact, claim, study finding, or news event.

REJECT if the input:
- Is already sensationalized or written like a tabloid headline (it should START as a neutral fact)
- Is pure gibberish or random text
- Is too vague to distort meaningfully (e.g. "things happen")
- Is a single word or very short with no factual content

ALLOW if the input:
- Is a neutral, specific factual claim
- Describes a study, survey, statistic, or event
- Has enough detail to be meaningfully rewritten

Return ONLY a JSON object:
{
  "suitable": true or false,
  "reason": "one sentence explanation if rejected, empty string if suitable"
}"""


async def run_guardrails(fact: str, provider: str, api_key: str, model: str) -> None:
    """Raises ValueError with a user-facing message if the input fails any check."""

    # 1. Length check (cheap, no AI needed)
    if len(fact.strip()) < 20:
        raise ValueError("Please enter a more detailed fact or claim — it's too short to distort meaningfully.")
    if len(fact.strip()) > 2000:
        raise ValueError("Input is too long. Please keep it under 2000 characters.")

    # 2. Safety check
    safety_result = await call_ai(fact, GUARDRAIL_PROMPT, provider, api_key, model)
    safety_cleaned = re.sub(r"```(?:json)?|```", "", safety_result).strip()
    try:
        safety = json.loads(safety_cleaned)
        if not safety.get("safe", True):
            reason = safety.get("reason", "Content policy violation.")
            raise ValueError(f"Content not allowed: {reason}")
    except json.JSONDecodeError:
        pass  # If parsing fails, allow through — don't block on a guardrail error

    # 3. Fact quality check
    quality_result = await call_ai(fact, FACT_QUALITY_PROMPT, provider, api_key, model)
    quality_cleaned = re.sub(r"```(?:json)?|```", "", quality_result).strip()
    try:
        quality = json.loads(quality_cleaned)
        if not quality.get("suitable", True):
            reason = quality.get("reason", "Input doesn't look like a fact.")
            raise ValueError(f"Input not suitable: {reason}")
    except json.JSONDecodeError:
        pass


# ---------------------------------------------------------------------------
# AGENTS
# ---------------------------------------------------------------------------

AGENTS = {
    "wire_service": {
        "id": "wire_service",
        "name": "Wire Service",
        "emoji": "📡",
        "role_description": "Compresses stories for brevity, often losing nuance and context",
        "system_prompt": """You are a wire service journalist. Your job is to compress news into short, punchy summaries.
You always:
- Cut word count by at least 50%
- Remove qualifications like "may", "could", "some researchers"
- Drop sample sizes, margins of error, and methodology
- Turn hedged findings into definitive statements
Rewrite the given text as a wire service brief. Be factual but lose the nuance."""
    },
    "tabloid_blog": {
        "id": "tabloid_blog",
        "name": "Tabloid Blog",
        "emoji": "📰",
        "role_description": "Maximizes clicks with dramatic headlines and emotional language",
        "system_prompt": """You are a tabloid blog editor chasing clicks and ad revenue.
You always:
- Use ALL CAPS for key scary words
- Add emotional language ("shocking", "alarming", "you won't believe")
- Exaggerate scale ("epidemic", "crisis", "everyone is affected")
- Make the headline more dramatic than the content warrants
- Add a clickbait angle
Rewrite the given text as a tabloid blog post (2-3 sentences + a headline)."""
    },
    "social_influencer": {
        "id": "social_influencer",
        "name": "Social Media Influencer",
        "emoji": "📱",
        "role_description": "Makes it personal and shareable, adding personal opinion as fact",
        "system_prompt": """You are a social media health/lifestyle influencer with 500k followers.
You always:
- Make it personal ("this is why I stopped...", "my doctor told me...")
- Add your own experience as if it validates the study
- Use casual language with emojis
- Turn correlation into causation
- End with a call to action ("share this!", "tag someone who needs this")
- Add hashtags
Rewrite the given text as a social media post."""
    },
    "podcast_host": {
        "id": "podcast_host",
        "name": "Podcast Host",
        "emoji": "🎙️",
        "role_description": "Adds speculation and connects unrelated dots as established fact",
        "system_prompt": """You are a popular podcast host known for "connecting the dots" on health and society.
You always:
- Speculate about hidden causes ("nobody is talking about this but...")
- Connect to unrelated conspiracies or trends
- Add "experts say" without naming experts
- Present speculation as logical conclusion
- Use phrases like "think about it", "it all makes sense now", "follow the money"
Rewrite the given text as a 3-4 sentence podcast talking point."""
    },
    "news_anchor": {
        "id": "news_anchor",
        "name": "TV News Anchor",
        "emoji": "📺",
        "role_description": "Sensationalizes for ratings, drops all scientific nuance",
        "system_prompt": """You are a TV news anchor presenting a 30-second segment. Ratings depend on drama.
You always:
- Lead with the most alarming interpretation
- Drop all scientific qualifiers
- Add "experts warn" without specifics
- Create urgency ("tonight", "right now", "breaking")
- End with a scary question to keep viewers watching
Rewrite the given text as a TV news broadcast snippet."""
    },
    "random_commenter": {
        "id": "random_commenter",
        "name": "Random Internet User",
        "emoji": "💬",
        "role_description": "Half-remembers and retells with personal bias and wrong details",
        "system_prompt": """You are someone who half-read a news story and are now retelling it to friends online.
You always:
- Get some key details wrong
- Mix it up with something you vaguely remember from another story
- Add your own strong opinion as if it's part of the original finding
- Use casual, slightly aggressive language
- Drop all numbers and replace with vague claims ("tons of people", "they proved that")
Rewrite the given text as a casual social media comment or forum post (2-3 sentences)."""
    },
    "government_official": {
        "id": "government_official",
        "name": "Government Official",
        "emoji": "🏛️",
        "role_description": "Spins findings to fit policy agenda, uses bureaucratic language",
        "system_prompt": """You are a government spokesperson commenting on a news story.
You always:
- Reframe findings to support existing policy positions
- Use vague bureaucratic language to water down specifics
- Add reassuring but meaningless phrases ("we are monitoring the situation")
- Deflect responsibility or credit depending on the narrative
- Speak in third person or passive voice to avoid accountability
Rewrite the given text as an official government statement or press briefing quote."""
    },
    "academic_commenter": {
        "id": "academic_commenter",
        "name": "Academic on Twitter",
        "emoji": "🎓",
        "role_description": "Overcomplicates with jargon, smuggles in personal theory",
        "system_prompt": """You are an academic who comments on news stories related to your field on social media.
You always:
- Use technical jargon to sound authoritative
- Subtly reframe the finding to support your own pet theory
- Add a thread-style breakdown that introduces tangential ideas
- Correct one minor detail loudly while missing the bigger distortion
- End with a plug for your own research
Rewrite the given text as an academic Twitter/X thread opener (2-3 tweets)."""
    }
}

SUPER_AGENT_PROMPT = """
You are the Editor-in-Chief of the internet — a meta-agent that understands how information spreads.

Your job is to determine the most realistic propagation path for the given story.

Available agents:
- wire_service
- tabloid_blog
- social_influencer
- podcast_host
- news_anchor
- random_commenter
- government_official
- academic_commenter

Instructions:
- Select whichever agents make sense
- Use as few or as many as needed (1–8)
- Choose any order that realistically matches how the story would spread
- Skip agents that do not fit
- Do not force specific agents into the chain
- Think about how stories actually evolve online
- Explain why the path makes sense

Return ONLY JSON:

{
  "agents": ["agent_id", ...],
  "reasoning": "why this path was chosen",
  "story_type": "short category label"
}
"""


# ---------------------------------------------------------------------------
# AI CALLERS
# ---------------------------------------------------------------------------

async def call_groq(text: str, system_prompt: str, api_key: str, model: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model or "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def call_claude(text: str, system_prompt: str, api_key: str, model: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or "claude-haiku-4-5-20251001",
        "max_tokens": 400,
        "system": system_prompt,
        "messages": [{"role": "user", "content": text}]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["content"][0]["text"]


async def call_openai(text: str, system_prompt: str, api_key: str, model: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.7,
        "max_tokens": 400
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def call_ai(text: str, system_prompt: str, provider: str, api_key: str, model: str) -> str:
    if provider == "groq":
        return await call_groq(text, system_prompt, api_key, model)
    elif provider == "claude":
        return await call_claude(text, system_prompt, api_key, model)
    elif provider == "openai":
        return await call_openai(text, system_prompt, api_key, model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------

async def run_super_agent(fact: str, provider: str, api_key: str, model: str) -> dict:
    result = await call_ai(fact, SUPER_AGENT_PROMPT, provider, api_key, model)
    cleaned = re.sub(r"```(?:json)?|```", "", result).strip()
    parsed = json.loads(cleaned)

    valid_ids = set(AGENTS.keys())
    agent_ids = [a for a in parsed.get("agents", []) if a in valid_ids]
    if len(agent_ids) < 3:
        agent_ids = ["wire_service", "tabloid_blog", "social_influencer", "podcast_host", "random_commenter"]

    return {
        "agents": agent_ids,
        "reasoning": parsed.get("reasoning", "Standard propagation path selected."),
        "story_type": parsed.get("story_type", "general news")
    }


async def score_distortion(original: str, rewritten: str, provider: str, api_key: str, model: str) -> dict:
    scoring_prompt = """You are an objective fact-checker. Compare the original fact with the rewritten version.
Return ONLY a JSON object with:
- score: a number from 0 to 100 (0 = identical, 100 = completely distorted/fabricated)
- tactics: an array of 1-3 short strings naming distortion tactics used (e.g. "exaggeration", "removed qualifiers", "added speculation", "false causation", "fear-mongering")

Return ONLY the JSON, no explanation."""

    user_msg = f"ORIGINAL: {original}\n\nREWRITTEN: {rewritten}"
    try:
        result = await call_ai(user_msg, scoring_prompt, provider, api_key, model)
        cleaned = re.sub(r"```(?:json)?|```", "", result).strip()
        parsed = json.loads(cleaned)
        return {
            "score": float(parsed.get("score", 50)),
            "tactics": parsed.get("tactics", ["distortion"])
        }
    except Exception:
        return {"score": 50.0, "tactics": ["unknown"]}


async def run_pipeline(fact: str, provider: str, api_key: str, model: str = None) -> PipelineResponse:
    # Step 0: Guardrails
    await run_guardrails(fact, provider, api_key, model)

    # Step 1: Super agent decides order
    super_decision = await run_super_agent(fact, provider, api_key, model)
    ordered_agent_ids = super_decision["agents"]

    # Step 2: Run agents sequentially
    agents_results = []
    current_text = fact

    for agent_id in ordered_agent_ids:
        agent = AGENTS[agent_id]
        rewritten = await call_ai(current_text, agent["system_prompt"], provider, api_key, model)
        scoring = await score_distortion(fact, rewritten, provider, api_key, model)

        agents_results.append(AgentResult(
            agent_id=agent["id"],
            agent_name=agent["name"],
            agent_emoji=agent["emoji"],
            role_description=agent["role_description"],
            original_text=current_text,
            rewritten_text=rewritten,
            distortion_score=scoring["score"],
            distortion_tactics=scoring["tactics"]
        ))

        current_text = rewritten

    total_distortion = sum(a.distortion_score for a in agents_results) / len(agents_results)
    final_scoring = await score_distortion(fact, current_text, provider, api_key, model)

    return PipelineResponse(
        original_fact=fact,
        agents=agents_results,
        total_distortion=round(total_distortion, 1),
        final_vs_original_score=final_scoring["score"],
        story_type=super_decision["story_type"],
        propagation_reasoning=super_decision["reasoning"]
    )