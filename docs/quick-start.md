# Quick Start

Get Forge running in 5 minutes.

## Prerequisites

- Python 3.12+
- Node.js 18+
- API key (OpenAI, Anthropic, etc.)

## Installation

```bash
# 1. Clone
git clone https://github.com/All-Hands-AI/Forge.git
cd Forge

# 2. Install Python deps
poetry install
# OR: pip install -e .

# 3. Install frontend deps
cd frontend && npm install && cd ..

# 4. Set API key
export FORGE_API_KEY="your-api-key"
# OR edit config.toml: [llm] api_key = "your-api-key"
```

## Run

```bash
# Terminal 1: Backend
forge start

# Terminal 2: Frontend
cd frontend && npm run dev
```

## Verify

1. Open http://localhost:3001
2. Create a conversation
3. Ask: "Create a simple HTML page"

## Next Steps

- [Getting Started](./getting_started.md) - Full setup guide
- [Tool Quick Reference](./tool-quick-reference.md) - All tools
- [Production Deployment](./production-setup.md) - SaaS deployment

## Troubleshooting

**Backend won't start?**
```bash
# Check Python version
python --version  # Should be 3.12+

# Reinstall
pip install -e .
```

**Frontend won't start?**
```bash
cd frontend
rm -rf node_modules
npm install
```

**No API key?**
- Get one from OpenAI, Anthropic, or your LLM provider
- Set in environment or `config.toml`

See [Common Issues](./common-issues.md) for more help.

