# Echo Chambers - Misinformation Propagation Simulator

An educational web service that demonstrates how factual information gets progressively distorted as it spreads through different media channels and social networks.

## Overview

**Echo Chambers** is a FastAPI-based application that takes a neutral fact or claim and simulates its transformation as it passes through various stages of the media ecosystem. Each "agent" represents a different type of media actor—from wire services to tabloid blogs to social media influencers—each with their own style of distortion and sensationalism.

This tool is designed for:
- **Media literacy education**: Understanding how misinformation spreads
- **Journalism professionals**: Studying distortion patterns
- **Researchers**: Analyzing propaganda techniques
- **Content creators**: Learning about media bias and echo chambers

## How It Works

### The Pipeline

1. **Guardrails**: Safety checks ensure the input is appropriate and contains sufficient detail
2. **Super Agent**: Decides the realistic propagation order for the given fact
3. **Sequential Distortion**: The fact passes through 4-6 agents in realistic order, each distorting it according to their characterization
4. **Scoring**: Each transformation is scored for distortion and tactics used

### Agent Types

The system includes 8 distinct agent personas:

| Agent | Emoji | Role |
|-------|-------|------|
| **Wire Service** | 📡 | Compresses for brevity, removes nuance |
| **Tabloid Blog** | 📰 | Maximizes clicks with dramatic language |
| **Social Media Influencer** | 📱 | Personalizes and adds anecdotal "evidence" |
| **Podcast Host** | 🎙️ | Connects dots and entertains with speculation |
| **TV News Anchor** | 📺 | Sensationalizes for ratings |
| **Random Internet User** | 💬 | Half-remembers with personal bias |
| **Government Official** | 🏛️ | Spins to fit policy agenda |
| **Academic on Twitter** | 🎓 | Overcomplicates with jargon |

## Features

- ✅ **Real-world propagation paths**: Not all agents run on every fact type—selection is intelligent
- ✅ **Multiple AI providers**: Support for Groq, OpenAI, and Anthropic Claude
- ✅ **Distortion scoring**: Each transformation is scored 0-100 for severity
- ✅ **Tactic identification**: System identifies specific distortion techniques used
- ✅ **Content safety**: Built-in guardrails prevent harmful inputs
- ✅ **CORS enabled**: Ready for web frontend integration
- ✅ **Async processing**: High-performance async/await architecture

## Installation

### Prerequisites
- Python 3.10+
- pip

### Setup

1. Clone the repository:
```bash
git clone <repository>
cd EchoChambers
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root:
```bash
GROQ_API_KEY=your_groq_api_key_here
```

You can also use OpenAI or Claude by setting:
- `OPENAI_API_KEY` for OpenAI
- `ANTHROPIC_API_KEY` for Claude

## Usage

### Running the Server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### Health Check
```
GET /
```
Returns:
```json
{
  "message": "Misinformation Pipeline API is running"
}
```

#### Analyze a Fact
```
POST /api/analyze
```

**Request:**
```json
{
  "fact": "A study found that people who drink 3-4 cups of coffee daily have a 24% lower risk of heart disease compared to those who don't drink coffee."
}
```

**Response:**
```json
{
  "original_fact": "A study found that people who drink 3-4 cups of coffee daily have a 24% lower risk of heart disease compared to those who don't drink coffee.",
  "agents": [
    {
      "agent_id": "wire_service",
      "agent_name": "Wire Service",
      "agent_emoji": "📡",
      "role_description": "Compresses stories for brevity, often losing nuance and context",
      "original_text": "...",
      "rewritten_text": "Coffee consumption linked to lower heart disease risk.",
      "distortion_score": 15.5,
      "distortion_tactics": ["removed qualifiers", "oversimplification"]
    },
    ...
  ],
  "total_distortion": 42.3,
  "final_vs_original_score": 68.7,
  "story_type": "health/science",
  "propagation_reasoning": "Health findings move through wire services first, then influencers and media outlets amplify."
}
```

## API Response Schema

### PipelineResponse
```ts
{
  original_fact: string;           // The input fact
  agents: AgentResult[];           // Results from each agent
  total_distortion: number;        // Average distortion score (0-100)
  final_vs_original_score: number; // How distorted the final version is
  story_type: string;              // Category of the story
  propagation_reasoning: string;   // Why this path was chosen
}
```

### AgentResult
```ts
{
  agent_id: string;           // Unique identifier
  agent_name: string;         // Display name
  agent_emoji: string;        // Visual icon
  role_description: string;   // What this agent does
  original_text: string;      // Input to this agent
  rewritten_text: string;     // Output from this agent
  distortion_score: float;    // 0-100, higher = more distorted
  distortion_tactics: string[]; // List of techniques used
}
```

## Error Handling

The API returns helpful error messages:

**400 - Bad Request**: Empty or too-short fact
```json
{
  "detail": "Please enter a more detailed fact or claim — it's too short to distort meaningfully."
}
```

**500 - Content Policy or Processing Error**:
```json
{
  "detail": "Content not allowed: Targets a real, named living person..."
}
```

## Architecture

### Project Structure
```
EchoChambers/
├── main.py              # FastAPI app & routes
├── agents.py            # Core pipeline logic & agent definitions
├── models.py            # Pydantic data models
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
└── README.md           # This file
```

### Key Components

**main.py**: FastAPI application with REST endpoints
- Health check endpoint
- Analyze endpoint with request validation

**agents.py**: Core business logic
- Guardrail safety checks (content policy, length, quality)
- 8 agent definitions with role descriptions and system prompts
- Super agent for intelligent agent ordering
- AI provider integration (Groq, OpenAI, Claude)
- Distortion scoring engine
- Main pipeline orchestrator

**models.py**: Data validation
- `FactRequest`: Input validation
- `AgentResult`: Single agent output
- `PipelineResponse`: Final API response

## Configuration

### AI Provider Selection

The default provider is **Groq** with the `llama-3.3-70b-versatile` model.

To use a different provider, modify the API call or environment setup:

**For OpenAI:**
```bash
OPENAI_API_KEY=sk-...
```

**For Claude (Anthropic):**
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Customization

You can customize agent behaviors by editing their `system_prompt` in `agents.py`. Each agent's persona and distortion style is controlled by its system prompt.

## Example Scenarios

### Political News
Input: "The Federal Reserve raised interest rates by 0.25% citing inflation concerns."

Path: Wire Service → News Anchor → Podcast Host → Random Commenter

Distortion: 58.3 / 100

### Health Claim
Input: "Researchers found that regular exercise reduces depression symptoms by 40% in clinical trials."

Path: Wire Service → Social Influencer → Tabloid Blog → Random Commenter

Distortion: 72.1 / 100

### Academic Research
Input: "A peer-reviewed study shows that 73% of misinformation in social media comes from 10% of users."

Path: Wire Service → Academic on Twitter → Podcast Host → Random Commenter

Distortion: 44.7 / 100

## Dependencies

- **fastapi**: Modern web framework
- **uvicorn**: ASGI server
- **httpx**: Async HTTP client for AI API calls
- **pydantic**: Data validation and serialization
- **python-dotenv**: Environment variable management

## Safety Features

The system includes multiple layers of protection:

1. **Content Policy Guardrail**: Rejects harmful content (hate speech, defamation, explicit content)
2. **Fact Quality Check**: Ensures input is specific and suitable for distortion
3. **Length Validation**: Between 20-2000 characters
4. **API Key Requirement**: Prevents unauthorized access

## Testing

Use the included `test_main.http` file with an HTTP client (VS Code REST Client, PostMan, etc.):

```http
POST http://localhost:8000/api/analyze
Content-Type: application/json

{
  "fact": "A recent study shows that people who sleep 7-8 hours per night have better cognitive performance than those who sleep less."
}
```

## Use Cases

- 📚 **Classroom tool** for teaching media literacy
- 🔍 **Research** on information distortion patterns
- 🎓 **Journalist training** on how facts get twisted
- 🛡️ **Content moderation** training
- 🧠 **Cognitive bias** demonstrations
- 📊 **Propaganda analysis** framework

## Ethical Use

This tool is designed for **educational purposes only**. It should be used to:
- Understand how misinformation spreads
- Develop critical thinking skills
- Study media bias and propaganda
- Train professionals in content verification

It should NOT be used to:
- Create actual misinformation
- Deceive audiences
- Spread harmful content
- Violate anyone's privacy or dignity

## Contributing

Suggestions for new agent types or improvements are welcome. To add a new agent:

1. Add entry to `AGENTS` dict in `agents.py`
2. Define `id`, `name`, `emoji`, `role_description`, and `system_prompt`
3. Update `SUPER_AGENT_PROMPT` to include selection logic

## License

MIT License - see LICENSE file for details

---

**Made with ❤️ to fight misinformation through education**

