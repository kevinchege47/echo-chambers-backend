import json
import re
import httpx
from models import AgentResult, PipelineResponse

AGENTS = [
    {
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
    {
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
    {
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
    {
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
    {
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
    {
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
    }
]


async def call_groq(text: str, system_prompt: str, api_key: str, model: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.8,
        "max_tokens": 400
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


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
        "messages": [
            {"role": "user", "content": text}
        ]
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def call_openai(text: str, system_prompt: str, api_key: str, model: str) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.8,
        "max_tokens": 400
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def call_ai(text: str, system_prompt: str, provider: str, api_key: str, model: str) -> str:
    if provider == "groq":
        return await call_groq(text, system_prompt, api_key, model)
    elif provider == "claude":
        return await call_claude(text, system_prompt, api_key, model)
    elif provider == "openai":
        return await call_openai(text, system_prompt, api_key, model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def score_distortion(original: str, rewritten: str, provider: str, api_key: str, model: str) -> dict:
    scoring_prompt = """You are an objective fact-checker. Compare the original fact with the rewritten version.
Return ONLY a JSON object with:
- score: a number from 0 to 100 (0 = identical, 100 = completely distorted/fabricated)
- tactics: an array of 1-3 short strings naming distortion tactics used (e.g. "exaggeration", "removed qualifiers", "added speculation", "false causation", "fear-mongering")

Return ONLY the JSON, no explanation."""

    user_msg = f"ORIGINAL: {original}\n\nREWRITTEN: {rewritten}"

    try:
        result = await call_ai(user_msg, scoring_prompt, provider, api_key, model)
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?|```", "", result).strip()
        parsed = json.loads(cleaned)
        return {
            "score": float(parsed.get("score", 50)),
            "tactics": parsed.get("tactics", ["distortion"])
        }
    except Exception:
        return {"score": 50.0, "tactics": ["unknown"]}


async def run_pipeline(fact: str, provider: str, api_key: str, model: str = None) -> PipelineResponse:
    agents_results = []
    current_text = fact

    for agent in AGENTS:
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
        final_vs_original_score=final_scoring["score"]
    )
