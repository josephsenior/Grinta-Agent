# 🔧 **Troubleshooting Guide**

> **Common issues, solutions, and debugging techniques for Forge**

---

## 📖 **Table of Contents**

- [Installation Issues](#installation-issues)
- [Backend Problems](#backend-problems)
- [Frontend Issues](#frontend-issues)
- [Performance Problems](#performance-problems)
- [WebSocket Errors](#websocket-errors)

---

## 📦 **Installation Issues**

### **Problem: Python dependencies fail to install**

**Symptoms:**
```bash
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**
1. Verify Python version (3.8+ required):
   ```bash
   python --version
   ```

2. Upgrade pip:
   ```bash
   python -m pip install --upgrade pip
   ```

3. Install in development mode:
   ```bash
   pip install -e .
   ```

4. If issues persist, try creating a fresh virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -e .
   ```

---

### **Problem: Node.js/pnpm installation fails**

**Symptoms:**
```bash
npm ERR! code EACCES
npm ERR! permission denied
```

**Solutions:**
1. Use Node Version Manager (nvm):
   ```bash
   nvm install 18
   nvm use 18
   ```

2. Clear pnpm store:
   ```bash
   pnpm store prune
   ```

3. Delete node_modules and reinstall:
   ```bash
   rm -rf node_modules pnpm-lock.yaml
   pnpm install
   ```

---

## 🖥️ **Backend Problems**

### **Problem: Backend fails to start**

**Symptoms:**
```bash
ModuleNotFoundError: No module named 'Forge'
```

**Solutions:**
1. Ensure you're in the correct directory:
   ```bash
   cd Forge
   ```

2. Verify installation:
   ```bash
   pip list | grep Forge
   ```

3. Reinstall in development mode:
   ```bash
   pip install -e .
   ```

---

### **Problem: 500 Internal Server Error**

**Symptoms:**
- API endpoints return 500 errors
- Console shows stack traces

**Solutions:**
1. Check backend logs for detailed error:
   ```bash
   # Check uvicorn.err in logs directory
   cat logs/uvicorn.err
   ```

2. Verify environment variables:
   ```bash
   # Check .env file
   cat .env
   ```

3. Check LLM provider configuration:
   ```bash
   # Ensure API keys are set
   echo $OPENAI_API_KEY
   ```

4. Reset database if needed:
   ```bash
   python -m Forge.db.reset
   ```

---

### **Problem: Database connection errors**

**Symptoms:**
```
sqlalchemy.exc.OperationalError: unable to open database file
```

**Solutions:**
1. Check database path in config:
   ```toml
   [database]
   url = "sqlite:///./Forge.db"
   ```

2. Ensure directory permissions:
   ```bash
   chmod 755 .
   ```

3. Create database directory:
   ```bash
   mkdir -p data
   ```

---

## 🎨 **Frontend Issues**

### **Problem: Frontend won't start**

**Symptoms:**
```bash
Error: Cannot find module 'vite'
```

**Solutions:**
1. Ensure you're in frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Clear cache and reinstall:
   ```bash
   rm -rf node_modules .vite pnpm-lock.yaml
   pnpm install
   ```

---

### **Problem: Hydration mismatch errors**

**Symptoms:**
```
Hydration failed because the server rendered HTML didn't match the client
```

**Solutions:**
1. This is usually non-critical. Clear browser cache:
   - Chrome: Ctrl+Shift+Delete
   - Firefox: Ctrl+Shift+Delete

2. Hard refresh page:
   - Chrome/Firefox: Ctrl+Shift+R
   - Safari: Cmd+Shift+R

3. Check for client-side only code:
   ```tsx
   // Ensure client-side checks
   const [isClient, setIsClient] = useState(false);
   
   useEffect(() => {
     setIsClient(true);
   }, []);
   
   if (!isClient) return null;
   ```

---

### **Problem: React Flow warnings**

**Symptoms:**
```
[React Flow]: It looks like you've created a new nodeTypes object
```

**Solutions:**
1. Define nodeTypes outside component:
   ```tsx
   const FLOW_NODE_TYPES = {
     custom: CustomNode,
   } as const;
   
   // Inside component
   <ReactFlow nodeTypes={FLOW_NODE_TYPES} />
   ```

2. Or use useMemo:
   ```tsx
   const nodeTypes = useMemo(() => ({
     custom: CustomNode,
   }), []);
   ```

---

## ⚡ **Performance Problems**

### **Problem: Slow agent responses**

**Symptoms:**
- Long wait times (>30 seconds)
- Timeouts

**Solutions:**
1. Check network connection

2. Try a different LLM provider:
   ```bash
   # In .env
   FORGE_LLM_PROVIDER=anthropic
   FORGE_LLM_MODEL=claude-3-sonnet
   ```

3. Reduce max_tokens:
   ```toml
   [llm]
   max_tokens = 2000  # Instead of 4000
   ```

4. Check API rate limits

---

### **Problem: High memory usage**

**Symptoms:**
- System becomes slow
- Out of memory errors

**Solutions:**
1. Limit concurrent agents:
   ```toml
   [system]
   max_concurrent_agents = 3
   ```

2. Clear conversation history:
   ```bash
   # In frontend
   Click "New Conversation"
   ```

3. Restart backend:
   ```bash
   # Kill process
   pkill -f Forge.server
   
   # Restart
   python -m Forge.server
   ```

---

## 🔌 **WebSocket Errors**

### **Problem: WebSocket connection fails**

**Symptoms:**
```
Socket.IO connection to 'http://localhost:3000/socket.io' failed
```

**Solutions:**
1. Verify backend is running:
   ```bash
   curl http://localhost:3000/health
   ```

2. Check CORS configuration:
   ```python
   # In backend
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
   )
   ```

3. Verify WebSocket URL:
   ```bash
   # In frontend .env
   VITE_WEBSOCKET_URL=http://localhost:3000/socket.io
   ```

---

### **Problem: WebSocket disconnects frequently**

**Symptoms:**
- "WebSocket disconnected" messages
- Need to refresh often

**Solutions:**
1. Check network stability

2. Increase timeout:
   ```python
   # In backend WebSocket config
   timeout = 60  # seconds
   ```

3. Enable auto-reconnect (already enabled):
   ```typescript
   // Frontend handles auto-reconnect
   ```

---

## 🆘 **Getting Help**

If you've tried the above solutions and still have issues:

### **1. Check Logs:**
```bash
# Backend logs
tail -f logs/uvicorn.err

# Browser console
Press F12 → Console tab
```

### **2. Enable Debug Mode:**
```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

### **3. Create an Issue:**
Include:
- Operating system
- Python version
- Node.js version
- Full error message
- Steps to reproduce
- Logs (backend and browser console)

### **4. Community Support:**
- GitHub Discussions
- Discord server
- Stack Overflow (tag: Forge)

---

## 📚 **Additional Resources**

- [Getting Started Guide](getting-started.md)
- [Best Practices](best-practices.md)
- [Configuration Guide](../configuration/system-config.md)
- [API Documentation](../api/rest-api.md)

---

**Remember:** Most issues have simple solutions. Check logs first, verify configuration, and don't hesitate to ask for help!

