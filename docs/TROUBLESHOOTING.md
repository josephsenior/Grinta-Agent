# Troubleshooting Guide

## Common Issues

### LLM & API Key Issues

#### "No API key found for provider: anthropic"

**Cause:** Anthropic API key not set in environment

**Solution:**
```bash
# Add to .env file:
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Restart backend
poetry run python -m openhands.server.listen
```

**Verify:**
```bash
# Check environment variable is loaded
echo $ANTHROPIC_API_KEY  # Should print your key
```

#### "API key format validation failed"

**Cause:** Wrong API key format for provider

**Common Mistakes:**
- Using OpenAI key (sk-...) for Anthropic (needs sk-ant-...)
- Using Anthropic key for OpenRouter (needs sk-or-...)

**Solution:**
```bash
# Check which provider you're using
# In .env:
LLM_MODEL=claude-sonnet-4-20250514  # → Needs ANTHROPIC_API_KEY (sk-ant-...)
LLM_MODEL=openrouter/gpt-4o         # → Needs OPENROUTER_API_KEY (sk-or-...)
LLM_MODEL=gpt-4o                    # → Needs OPENAI_API_KEY (sk-...)
```

**API Key Prefixes:**
| Provider | Prefix | Example |
|----------|--------|---------|
| OpenAI | `sk-` | sk-proj-abc123... |
| Anthropic | `sk-ant-` | sk-ant-api03-xyz... |
| OpenRouter | `sk-or-` | sk-or-v1-abc123... |
| Google (Gemini) | `AIza` | AIzaSyAbc123... |
| Groq | `gsk_` | gsk_abc123... |

#### "Rate limit exceeded"

**Cause:** Too many requests to LLM provider

**Solution:**
```bash
# Wait for rate limit to reset (check error message)
# Or switch to different model/provider

# In .env:
LLM_MODEL=gpt-4o-mini  # Cheaper model = higher rate limits
```

**Prevention:**
- Use cheaper models for simple tasks
- Enable prompt caching (Claude models)
- Implement backoff strategy

#### "LLM cost exceeds daily quota"

**Cause:** Daily cost limit reached ($1 for free tier)

**Solution:**
```bash
# Option 1: Wait until midnight (quota resets daily)

# Option 2: Increase quota in settings
# Settings → Budget → Increase daily limit

# Option 3: Use cheaper model
LLM_MODEL=claude-haiku-4-5-20251001  # Much cheaper than Sonnet
```

### Docker & Runtime Issues

#### "Docker daemon not running"

**Cause:** Docker is not started

**Solution:**

**Mac/Windows:**
```bash
# Start Docker Desktop application
```

**Linux:**
```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker on boot
sudo systemctl enable docker
```

**Verify:**
```bash
docker ps  # Should show running containers
```

#### "Port 3000 already in use"

**Cause:** Another process using port 3000

**Solution:**

**Find process:**
```bash
# Mac/Linux
lsof -i :3000

# Windows
netstat -ano | findstr :3000
```

**Fix:**
```bash
# Option 1: Kill process
kill -9 <PID>

# Option 2: Change port
# In .env:
PORT=3001
```

#### "Container failed to start"

**Cause:** Docker image not built or corrupted

**Solution:**
```bash
# Rebuild Docker images
docker-compose build --no-cache

# Remove old containers
docker-compose down -v

# Start fresh
docker-compose up -d
```

### Database Issues

#### "Database connection failed"

**Cause:** Database not running or wrong credentials

**Solution:**
```bash
# Check DATABASE_URL in .env
DATABASE_URL=postgresql://user:pass@localhost:5432/openhands

# Test connection
psql $DATABASE_URL

# Or use SQLite for development
DATABASE_URL=sqlite:///./openhands.db
```

#### "Migration pending"

**Cause:** Database schema out of date

**Solution:**
```bash
# Run migrations
poetry run alembic upgrade head
```

### WebSocket Issues

#### "WebSocket connection failed"

**Cause:** Backend not running or port mismatch

**Solution:**
```bash
# Check backend is running
curl http://localhost:3000/api/health

# Check WebSocket URL in frontend
# Should be: ws://localhost:3000/ws/...

# Restart both frontend and backend
```

#### "WebSocket disconnecting frequently"

**Cause:** Network issues or timeouts

**Solution:**
```bash
# Increase timeout in config
# config.toml:
[server]
websocket_timeout = 300  # 5 minutes
```

### Agent Execution Issues

#### "Agent stuck in loop"

**Cause:** Agent repeating same action

**What you'll see:**
```
Agent: Running command...
Observation: Error
Agent: Running same command again...
Observation: Same error
Agent: Running same command again...
```

**Solution:**
```bash
# Stop agent
Click [Stop] button in UI

# Or via API
POST /api/conversations/{id}/stop

# Check stuck detection logs
tail -f logs/openhands.log | grep "stuck"
```

**Prevention:**
- Circuit breaker will auto-pause after 3 failures
- Stuck detector will intervene after 5 identical actions

#### "Agent not executing actions"

**Cause:** Agent paused or waiting for confirmation

**Check:**
```bash
# Check agent state
GET /api/conversations/{id}/state

# Response should show:
{
  "state": "RUNNING"  // Not PAUSED or AWAITING_USER_CONFIRMATION
}
```

**Solution:**
```bash
# If paused: Resume agent
POST /api/conversations/{id}/resume

# If awaiting confirmation: Approve action
POST /api/conversations/{id}/confirm
```

#### "File edit failed"

**Cause:** File doesn't exist, permission issues, or invalid syntax

**Common Errors:**
```
FileNotFoundError: main.py not found
PermissionError: Cannot write to /etc/passwd
SyntaxError: Invalid Python syntax in edit
```

**Solution:**
```bash
# Check file exists
ls -la main.py

# Check file permissions
chmod 644 main.py

# Check syntax of proposed edit
# Agent will show diff before applying
```

### Frontend Issues

#### "UI not loading"

**Cause:** Frontend not started or build error

**Solution:**
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Check for errors in terminal
```

#### "WebSocket shows 'Disconnected'"

**Cause:** Backend not reachable

**Solution:**
```bash
# Check backend is running
curl http://localhost:3000/api/health

# Check WebSocket URL matches backend port
# In frontend/.env:
VITE_API_URL=http://localhost:3000
VITE_WS_URL=ws://localhost:3000
```

### Performance Issues

#### "Agent responses are slow"

**Cause:** LLM latency, large context, or rate limits

**Diagnostics:**
```bash
# Check p95 latency in Grafana
# http://localhost:3001/grafana

# Check if rate limited
tail -f logs/openhands.log | grep "rate"
```

**Solutions:**
```bash
# 1. Use faster model
LLM_MODEL=claude-haiku-4-5-20251001  # 2x faster than Sonnet

# 2. Enable prompt caching
[llm]
caching_prompt = true

# 3. Reduce context size
[llm]
max_message_chars = 20000  # Default: 30000
```

#### "High memory usage"

**Cause:** Large conversation history

**Solution:**
```bash
# Enable memory condensation
[memory]
enable_condensation = true
condense_threshold = 50  # Condense after 50 messages

# Or clear old conversations
DELETE /api/conversations/{old_conversation_id}
```

### Cost Issues

#### "Unexpected high costs"

**Cause:** Large token consumption

**Diagnostics:**
```bash
# Check cost breakdown
GET /api/analytics/usage?period=today

# Check which conversations are expensive
GET /api/analytics/conversations?sort=cost
```

**Solutions:**
```bash
# 1. Set daily budget
[cost]
daily_limit_usd = 1.00

# 2. Use cheaper model
LLM_MODEL=gpt-4o-mini           # $0.15/$0.60 per 1M tokens
LLM_MODEL=claude-haiku-4-5-...  # $1/$5 per 1M tokens

# 3. Enable caching
[llm]
caching_prompt = true  # Can reduce costs by 35%
```

## Debugging

### Enable Debug Logging

```bash
# In .env:
LOG_LEVEL=DEBUG
LOG_JSON=true

# View logs
tail -f logs/openhands.log
```

### Check Agent State

```bash
# Via API
curl http://localhost:3000/api/conversations/{id}/state

# In logs
grep "agent_state" logs/openhands.log
```

### Check Metrics

```bash
# Prometheus metrics
curl http://localhost:9090/metrics

# Grafana dashboards
open http://localhost:3001/grafana
```

### Trace Request Flow

```bash
# All logs include request_id for tracing
tail -f logs/openhands.log | grep "request_id=abc123"

# Follow full request lifecycle:
# 1. Request received (request_id logged)
# 2. Agent invoked
# 3. LLM called (with cost)
# 4. Action executed
# 5. Response sent
```

## Getting Help

### Before Asking for Help

1. **Check logs:** `logs/openhands.log`
2. **Check Grafana:** `http://localhost:3001/grafana`
3. **Search existing issues:** GitHub Issues
4. **Check this guide:** You're here! ✅

### Reporting Issues

**Good bug report includes:**
- Steps to reproduce
- Expected behavior
- Actual behavior
- Logs (with request_id)
- Environment (OS, Python version, Docker version)
- Model used
- Conversation ID (if applicable)

**Template:**
```markdown
## Bug Description
Agent fails to edit Python files with syntax errors.

## Steps to Reproduce
1. Send message: "Fix syntax error in main.py"
2. Agent attempts edit
3. Edit fails with SyntaxError

## Expected Behavior
Agent should handle syntax errors gracefully

## Actual Behavior
Agent crashes with unhandled exception

## Logs
request_id=abc123
error: SyntaxError: invalid syntax
```

### Community Resources

- **GitHub Issues:** Report bugs, request features
- **GitHub Discussions:** Ask questions, share ideas
- **Documentation:** All guides in `docs/`
- **Discord:** Community chat (link TBD)

## Advanced Debugging

### Agent Not Responding

```bash
# Check agent controller state
grep "AgentController" logs/openhands.log

# Check for deadlock
grep "waiting" logs/openhands.log

# Check circuit breaker
grep "circuit_breaker" logs/openhands.log
```

### Memory Leaks

```bash
# Monitor memory usage
docker stats

# Check for large conversations
SELECT id, COUNT(*) as message_count 
FROM conversations 
GROUP BY id 
ORDER BY message_count DESC;
```

### Database Issues

```bash
# Check database connections
# In PostgreSQL:
SELECT count(*) FROM pg_stat_activity;

# Check slow queries
SELECT query, total_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

## Performance Tuning

See [Performance Tuning Guide](./guides/performance-tuning.md) for advanced optimization.

## Still Stuck?

Create an issue on GitHub with:
- Full error message
- Request ID from logs  
- Steps to reproduce
- Your environment details

We're here to help! 🚀

