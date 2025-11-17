# ⚡ **Performance Tuning Guide**

> **Optimization tips and techniques for maximum Forge performance**

---

## 📖 **Table of Contents**

- [Backend Optimization](#backend-optimization)
- [Frontend Optimization](#frontend-optimization)
- [Database Tuning](#database-tuning)
- [LLM Optimization](#llm-optimization)
- [Network Optimization](#network-optimization)
- [Monitoring Performance](#monitoring-performance)

---

## 🖥️ **Backend Optimization**

### **1. Python Performance**

**Use Production-Grade Server:**
```bash
# Development (single worker)
python -m forge.server

# Or with uvicorn directly:
uvicorn forge.server.listen:app --host 0.0.0.0 --port 3000

# Production (multiple workers)
gunicorn forge.server.listen:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:3000
```

**Configure Workers:**
```python
# config.toml
[server]
workers = 4  # CPU cores × 2
worker_timeout = 300  # seconds
```

**Enable Async Processing:**
```python
# Use async/await for I/O operations
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

---

### **2. Caching Strategies**

**In-Memory Cache:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_profile(user_id: str):
    # Expensive operation
    return fetch_from_db(user_id)
```

**Redis Cache:**
```python
import redis

cache = redis.Redis(host='localhost', port=6379)

def get_cached_data(key: str):
    if cached := cache.get(key):
        return json.loads(cached)
    
    data = expensive_operation()
    cache.setex(key, 3600, json.dumps(data))
    return data
```

---

### **3. Connection Pooling**

**Database Connections:**
```python
# SQLAlchemy with connection pool
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

**HTTP Connections:**
```python
# Reuse HTTP client
client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
    )
)
```

---

## 🎨 **Frontend Optimization**

### **1. Bundle Optimization**

**Code Splitting:**
```tsx
// Lazy load routes
const MetaSOPPanel = lazy(() => 
  import('./components/metasop/MetaSOPPanel')
);

// Use with Suspense
<Suspense fallback={<LoadingSpinner />}>
  <MetaSOPPanel />
</Suspense>
```

**Analyze Bundle:**
```bash
# Build with analysis
npm run build -- --analyze

# Check bundle size
npm run build
ls -lh dist/assets/*.js
```

**Target Sizes:**
- Initial bundle: < 200KB gzipped
- Total bundle: < 1MB gzipped
- Largest chunk: < 500KB gzipped

---

### **2. React Performance**

**Memoization:**
```tsx
// Memoize expensive components
const ExpensiveComponent = React.memo<Props>(({ data }) => {
  return <div>{/* ... */}</div>;
});

// Memoize expensive computations
const sortedData = useMemo(() => 
  data.sort((a, b) => a.value - b.value),
  [data]
);

// Memoize callbacks
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);
```

**Virtualization:**
```tsx
import { FixedSizeList } from 'react-window';

// For large lists (1000+ items)
<FixedSizeList
  height={500}
  itemCount={items.length}
  itemSize={50}
  width="100%"
>
  {({ index, style }) => (
    <div style={style}>{items[index]}</div>
  )}
</FixedSizeList>
```

---

### **3. Image Optimization**

**Use Modern Formats:**
```tsx
<picture>
  <source srcSet="image.avif" type="image/avif" />
  <source srcSet="image.webp" type="image/webp" />
  <img src="image.jpg" alt="..." loading="lazy" />
</picture>
```

**Lazy Loading:**
```tsx
<img 
  src="image.jpg" 
  loading="lazy" 
  decoding="async"
  alt="..."
/>
```

---

## 🗄️ **Database Tuning**

### **1. Query Optimization**

**Add Indexes:**
```sql
-- Index frequently queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

-- Composite indexes for multi-column queries
CREATE INDEX idx_messages_conv_timestamp 
  ON messages(conversation_id, timestamp);
```

**Analyze Slow Queries:**
```sql
-- PostgreSQL
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'test@example.com';

-- SQLite
EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'test@example.com';
```

---

### **2. Connection Management**

**Pool Configuration:**
```toml
[database]
pool_size = 20
max_overflow = 10
pool_timeout = 30
pool_recycle = 3600
```

**Monitor Connections:**
```python
# Check active connections
SELECT count(*) FROM pg_stat_activity;
```

---

## 🤖 **LLM Optimization**

### **1. Prompt Efficiency**

**Minimize Token Usage:**
```python
# ❌ Bad: Verbose prompt
prompt = """
Please analyze the following code and provide a detailed 
explanation of what it does, including all the functions,
variables, and any potential issues you might find...
"""

# ✅ Good: Concise prompt
prompt = """
Analyze this code:
- Purpose
- Key functions
- Issues
"""
```

**Cache Prompt Results:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_llm_response(prompt: str, temperature: float):
    return llm.generate(prompt, temperature=temperature)
```

---

### **2. Model Selection**

**Choose Appropriate Models:**
```python
# Simple tasks: Fast, cheap models
simple_task → "gpt-3.5-turbo"

# Complex tasks: Powerful models
complex_task → "gpt-4"

# Code generation: Specialized models
code_task → "claude-3-sonnet"
```

**Model Configuration:**
```toml
[llm]
# Reduce tokens for faster responses
max_tokens = 2000

# Lower temperature for consistency
temperature = 0.3

# Streaming for better UX
stream = true
```

---

### **3. Parallel Processing**

**Concurrent Requests:**
```python
import asyncio

# Execute multiple LLM calls concurrently
results = await asyncio.gather(
    llm.generate(prompt1),
    llm.generate(prompt2),
    llm.generate(prompt3),
)
```

---

## 🌐 **Network Optimization**

### **1. API Response Optimization**

**Compression:**
```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Response Caching:**
```python
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@app.get("/api/data")
@cache(expire=3600)  # Cache for 1 hour
async def get_data():
    return expensive_data_fetch()
```

---

### **2. WebSocket Optimization**

**Message Batching:**
```python
# Batch small messages
messages = []
async def send_batch():
    if messages:
        await websocket.send_json({"batch": messages})
        messages.clear()

# Send every 100ms or when batch reaches 10
asyncio.create_task(periodic_send())
```

**Binary Protocol:**
```python
# Use binary for large data
import msgpack

data = msgpack.packb(large_object)
await websocket.send_bytes(data)
```

---

## 📊 **Monitoring Performance**

### **1. Backend Metrics**

**Add Instrumentation:**
```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper
```

---

### **2. Frontend Metrics**

**Web Vitals:**
```typescript
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

getCLS(console.log);  // Cumulative Layout Shift
getFID(console.log);  // First Input Delay
getFCP(console.log);  // First Contentful Paint
getLCP(console.log);  // Largest Contentful Paint
getTTFB(console.log); // Time to First Byte
```

**Performance Targets:**
- LCP: < 2.5s (Good)
- FID: < 100ms (Good)
- CLS: < 0.1 (Good)
- TTFB: < 600ms (Good)

---

### **3. Lighthouse Audits**

**Run Audits:**
```bash
# Install Lighthouse
npm install -g lighthouse

# Run audit
lighthouse http://localhost:3000 \
  --output html \
  --output-path ./lighthouse-report.html

# Target scores
Performance: > 90
Accessibility: > 90
Best Practices: > 90
SEO: > 90
```

---

## 🎯 **Performance Checklist**

### **Backend:**
- [ ] Using production server (Gunicorn)
- [ ] Connection pooling configured
- [ ] Caching implemented (Redis/in-memory)
- [ ] Async operations for I/O
- [ ] Database indexes added
- [ ] Query optimization done

### **Frontend:**
- [ ] Bundle size < 200KB gzipped
- [ ] Code splitting implemented
- [ ] Images optimized (WebP/AVIF)
- [ ] Lazy loading enabled
- [ ] React components memoized
- [ ] Large lists virtualized

### **LLM:**
- [ ] Appropriate models selected
- [ ] Prompts optimized for tokens
- [ ] Streaming enabled
- [ ] Response caching implemented
- [ ] Parallel processing where possible

### **Network:**
- [ ] Compression enabled (gzip/brotli)
- [ ] Response caching configured
- [ ] WebSocket optimized
- [ ] CDN for static assets

### **Monitoring:**
- [ ] Performance metrics tracked
- [ ] Lighthouse scores > 90
- [ ] Error tracking enabled
- [ ] Resource usage monitored

---

## 📈 **Expected Improvements**

Following this guide should achieve:

- **50-70% reduction** in page load time
- **40-60% reduction** in API response time
- **30-50% reduction** in token usage
- **20-30% reduction** in server costs
- **90+ Lighthouse scores** across all metrics

---

**Remember:** Measure before and after optimization to verify improvements!

