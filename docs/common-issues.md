# Common Issues

Quick fixes for the most common problems.

## Setup Issues

### ❌ "Python dependencies fail to install"

**Fix:**
```bash
python --version  # Should be 3.12+
pip install --upgrade pip
pip install -e .
```

### ❌ "Node.js/npm installation fails"

**Fix:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### ❌ "ModuleNotFoundError: No module named 'openhands'"

**Fix:**
```bash
pip install -e .
# OR
poetry install
```

## Runtime Issues

### ❌ "Runtime crashes on file operations"

**Fix:**
- Check Docker is running: `docker ps`
- Restart backend: `forge start`
- Check logs: `cat logs/uvicorn.err`

### ❌ "Agent returns ERROR state and won't recover"

**Fix:**
- Refresh page (Ctrl+Shift+R)
- Check WebSocket connection (look for connection errors in console)
- Restart backend

### ❌ "Streaming shows all at once (not character-by-character)"

**Fix:**
- Clear browser cache
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Check browser console for errors

## File Operations

### ❌ "No such file or directory" when creating files

**Cause:** Agent tried to use `ultimate_editor` on a new file.

**Fix:** Agent should use `str_replace_editor` with `create` command. This is fixed in the latest prompt.

### ❌ "Replace failed" on new files

**Fix:** Use `str_replace_editor(command="create", ...)` for new files, not `ultimate_editor`.

## API / LLM Issues

### ❌ "500 Internal Server Error"

**Fix:**
```bash
# Check API key
echo $FORGE_API_KEY

# Check config
cat config.toml | grep api_key

# Check logs
tail -f logs/uvicorn.err
```

### ❌ "Rate limit exceeded" or "Quota exceeded"

**Fix:**
- Check your LLM provider account
- Reduce concurrent requests
- Use a different model (e.g., `gpt-3.5-turbo` instead of `gpt-4`)

## WebSocket Issues

### ❌ "WebSocket connection failed"

**Fix:**
- Check backend is running: `forge start`
- Check port 3001 is not blocked by firewall
- Try: `curl http://localhost:3001/health`

### ❌ "Agent state stuck in LOADING"

**Fix:**
- Refresh page
- Check runtime status in UI
- Restart backend

## Docker / Runtime Issues

### ❌ "Launch docker client failed"

**Fix:**
```bash
# Check Docker is running
docker ps

# If using Docker Desktop:
# Settings > Advanced > Allow default Docker socket
# Settings > Resources > Network > Enable host networking

# Restart Docker Desktop
```

### ❌ "Permission denied" errors

**Fix:**
```bash
# Fix ~/.openhands permissions
sudo chown -R $USER:$USER ~/.openhands
chmod 755 ~/.openhands
```

## Still Stuck?

1. Check [Troubleshooting Guide](./guides/troubleshooting.md) for detailed help
2. Check [Getting Started](./getting_started.md) for setup
3. Check backend logs: `tail -f logs/uvicorn.err`
4. Check frontend console (F12) for errors

