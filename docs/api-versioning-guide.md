# API Versioning Guide - Forge Production Implementation

*Implemented: November 4, 2025*

---

## 🎯 **Overview**

Forge now has **production-grade API versioning** that allows safe evolution without breaking existing clients.

### **Current Status:**
- ✅ Version infrastructure implemented
- ✅ Middleware active (adds version headers)
- ✅ Frontend config ready
- ⚠️ **Beta mode**: Non-versioned endpoints still work
- 🔜 **Post-launch**: Enforce `/api/v1/` prefix

---

## 📋 **Architecture**

### **1. Backend Versioning**

#### **Files Created:**
```python
Forge/server/versioning.py       # Versioning middleware + utilities
Forge/server/constants.py        # Version constants
```

#### **How It Works:**
```python
# Middleware automatically:
1. Detects API version from path (/api/v1/conversation)
2. Validates version is supported
3. Adds headers to response:
   - API-Version: v1
   - Deprecation: true (if deprecated)
   - Sunset: <date> (when version will be removed)
   - Link: <migration-guide> (how to migrate)
4. Logs deprecated version usage
```

---

### **2. Frontend Configuration**

#### **Files Created:**
```typescript
frontend/src/config/api-config.ts    # API versioning config
```

#### **Usage:**
```typescript
import { getAPIBase, buildAPIUrl, APIVersion } from "#/config/api-config";

// Get base URL (respects USE_VERSIONED_ENDPOINTS flag)
const base = getAPIBase();  // → "/api" (beta) or "/api/v1" (post-launch)

// Build versioned URL
const url = buildAPIUrl("/settings");  // → "/api/settings" (beta)

// Force specific version
const url = buildAPIUrl("/settings", { 
  version: APIVersion.V2,
  forceVersion: true 
});  // → "/api/v2/settings"
```

---

## 🚀 **Migration Strategy**

### **Phase 1: BETA (NOW - Next 3 Months)**

**Status:** Versioning infrastructure in place, non-versioned endpoints still work

**Configuration:**
```typescript
// frontend/src/config/api-config.ts
export const USE_VERSIONED_ENDPOINTS = false;  // ← Beta mode
```

```python
# Forge/server/constants.py  
ENFORCE_API_VERSIONING = False  # ← Beta mode (allows non-versioned)
```

**What this means:**
- ✅ Old endpoints work: `/api/settings`
- ✅ New endpoints work: `/api/v1/settings`
- ✅ You can change things freely
- ✅ Just communicate to beta users

**Actions During Beta:**
```markdown
1. Test versioned endpoints work
2. Iterate on API design freely
3. Gather feedback from beta users
4. Finalize v1 API shape
5. Update documentation
```

---

### **Phase 2: PRE-LAUNCH (1 Month Before)**

**Status:** Lock down v1, announce stability

**Actions:**
```markdown
1. Freeze v1 API shape (no more breaking changes)
2. Update all docs to show /api/v1/ paths
3. Announce to beta users:
   "v1 API is now stable. We commit to supporting it for 12+ months."
4. Test migration thoroughly
```

**Configuration:**
```typescript
// Frontend - still backward compatible
export const USE_VERSIONED_ENDPOINTS = false;  // ← Keep false for now
```

---

### **Phase 3: PUBLIC LAUNCH**

**Status:** v1 is stable, versioning enforced

**Configuration:**
```typescript
// frontend/src/config/api-config.ts
export const USE_VERSIONED_ENDPOINTS = true;  // ← Enable versioning!
```

```python
# Forge/server/constants.py
ENFORCE_API_VERSIONING = True  # ← Enforce strict versioning
```

**What changes:**
- ✅ All requests use `/api/v1/` prefix
- ❌ Non-versioned `/api/settings` returns error (or redirects to v1)
- ✅ Version headers on all responses
- ✅ Professional, production-ready

---

### **Phase 4: EVOLUTION (Month 6+)**

**Status:** Add v2 for new features

**When to add v2:**
```markdown
You need v2 when you want to make breaking changes:
- Rename fields (id → conversationId)
- Change response structure
- Remove deprecated endpoints
- Major feature additions
```

**Implementation:**
```python
# 1. Update versioning.py
class APIVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"  # ← Add v2

# 2. Mark v1 as deprecated (optional)
DEPRECATED_VERSIONS = {
    APIVersion.V1: {
        "message": "v1 is deprecated. Please migrate to v2.",
        "sunset_date": "2026-12-31",
        "migration_guide": "https://docs.forge.ai/api/v1-to-v2"
    }
}

# 3. Create v2 routes (keep v1 working!)
# Forge/server/routes/conversation_v2.py
app = APIRouter(prefix="/api/v2/conversations")

@app.get("/")
async def get_conversations_v2():
    return {
        "conversations": [...],  # New format
        "metadata": {...}        # New field
    }

# 4. Update frontend (gradual migration)
const url = buildAPIUrl("/settings", { version: APIVersion.V2 });
```

---

## 📖 **API Response Headers**

### **All API Responses Include:**

```http
HTTP/1.1 200 OK
API-Version: v1                          ← Current version used
X-RateLimit-Limit: 100                   ← Rate limit
X-RateLimit-Remaining: 95                ← Remaining requests
X-RateLimit-Reset: 1699564800            ← Reset timestamp
```

### **Deprecated Endpoints Also Include:**

```http
HTTP/1.1 200 OK
API-Version: v1
Deprecation: true                                           ← Version is deprecated
Sunset: Sat, 31 Dec 2026 23:59:59 GMT                      ← When it will be removed
Link: <https://docs.forge.ai/api/v1-to-v2>; rel="successor-version"  ← Migration guide
Warning: 299 - "v1 API is deprecated. Please migrate to v2."         ← Warning message
```

---

## 🛠️ **Developer Workflow**

### **Adding a New Endpoint (v1)**

```python
# Forge/server/routes/my_feature.py
from fastapi import APIRouter

app = APIRouter(prefix="/api/my-feature")

@app.get("/")
async def get_my_feature():
    return {"data": "..."}
```

```python
# Forge/server/app.py
from forge.server.routes.my_feature import app as my_feature_router

app.include_router(my_feature_router, tags=["v1", "my-feature"])
```

---

### **Adding a v2 Endpoint (Future)**

```python
# Forge/server/routes/my_feature_v2.py
from fastapi import APIRouter

app = APIRouter(prefix="/api/v2/my-feature")  # ← v2 prefix

@app.get("/")
async def get_my_feature_v2():
    return {
        "data": "...",
        "newField": "..."  # Breaking change!
    }
```

```python
# Forge/server/app.py
from forge.server.routes.my_feature_v2 import app as my_feature_v2_router

app.include_router(my_feature_v2_router, tags=["v2", "my-feature"])
```

**Both v1 and v2 work simultaneously!**

---

## 🎯 **Feature Flags (Gradual Rollout)**

### **Enable v2 for Specific Users:**

```typescript
// frontend/src/config/api-config.ts

// Check if user is in v2 beta
const userInV2Beta = localStorage.getItem("forge.v2-beta") === "true";

export const USE_V2_ENDPOINTS = userInV2Beta;

// Use different versions for different endpoints
export function getAPIBase(endpoint?: string): string {
  // Use v2 for specific endpoints
  if (USE_V2_ENDPOINTS && ["settings", "conversations"].includes(endpoint)) {
    return "/api/v2";
  }
  
  // Default to v1
  return USE_VERSIONED_ENDPOINTS ? "/api/v1" : "/api";
}
```

---

## 📊 **Monitoring (Track Version Usage)**

### **Backend Logging:**
```python
# Automatic in version_middleware
logger.info(f"API call: {version} - {path} - User: {user_id}")
```

### **Analytics Dashboard:**
```markdown
Track:
- v1 usage: 95% of requests
- v2 usage: 5% of requests
- Deprecated v1 usage: 2% (needs migration)

Goal: Migrate to 0% deprecated usage over 6 months
```

---

## 🔒 **Security Considerations**

### **Version Validation:**
```python
# Middleware automatically rejects unsupported versions:
GET /api/v99/settings

Response:
{
  "error": "unsupported_api_version",
  "message": "API version v99 is not supported",
  "supported_versions": ["v1", "v2"]
}
```

### **Prevent Path Traversal:**
```python
# Version extraction is safe:
path = "/api/../../etc/passwd"
version = get_api_version_from_path(path)  # → None (safe)
```

---

## 📚 **Documentation**

### **OpenAPI/Swagger Integration:**

After launch, update swagger to show versions:

```python
# Forge/server/app.py
app = FastAPI(
    title="Forge API",
    description="Multi-version API with backward compatibility",
    version=__version__,
    openapi_tags=[
        {"name": "v1", "description": "Stable API - v1 (current)"},
        {"name": "v2", "description": "Next-gen API - v2 (beta)"},
    ]
)
```

**URL:** `http://localhost:3000/docs`

**Will show:**
```
Endpoints by Version:
  v1 - Stable (current)
    - GET /api/v1/settings
    - POST /api/v1/conversation
    
  v2 - Next-gen (beta)
    - GET /api/v2/settings  (enhanced)
    - POST /api/v2/conversation  (multi-user)
```

---

## 🎯 **Migration Checklist**

### **Before Beta Launch:**
- ✅ Versioning infrastructure created
- ✅ Middleware active
- ✅ Frontend config ready
- ✅ Tags added to routes
- ⚠️ Test endpoints still work

### **During Beta (Next 3 Months):**
- [ ] Test version headers in responses
- [ ] Iterate on API design freely
- [ ] Finalize v1 API shape
- [ ] Write migration guides
- [ ] Update all documentation

### **Before Public Launch:**
- [ ] Set `USE_VERSIONED_ENDPOINTS = true`
- [ ] Set `ENFORCE_API_VERSIONING = True`
- [ ] Test all frontend calls use versioned URLs
- [ ] Announce v1 stability commitment
- [ ] Deploy with confidence!

---

## 💡 **Pro Tips**

### **1. Communicate Version in Mobile Apps:**
```typescript
// Store API version in app
const APP_API_VERSION = "v1";

// Include in requests
axios.get(`/api/${APP_API_VERSION}/settings`);

// When you release app v2.0:
const APP_API_VERSION = "v2";  // App update uses new API
```

---

### **2. Gradual Migration:**
```markdown
Week 1: Add /api/v2/settings (new endpoint)
Week 2: Frontend uses v2 for new users only
Week 3: Monitor v2 error rates
Week 4: Migrate 25% of users to v2
Week 8: Migrate 100% of users to v2
Month 6: Deprecate v1
Month 12: Remove v1 (sunset)
```

---

### **3. Emergency Rollback:**
```typescript
// If v2 has issues, rollback instantly:
export const USE_VERSIONED_ENDPOINTS = false;  // Back to v1
export const CURRENT_API_VERSION = APIVersion.V1;

// Deploy frontend → Everyone back on v1 ✅
```

---

## 🚨 **IMPORTANT: Beta Flexibility**

### **During Beta, You Can:**
- ✅ Change `/api/v1/` endpoints (beta = experimental)
- ✅ Add new fields
- ✅ Rename fields
- ✅ Change response formats
- ✅ Remove endpoints
- ✅ Completely redesign APIs

**Just notify your beta users!**

### **After Launch, You CANNOT:**
- ❌ Change `/api/v1/` endpoints (breaking change)
- ❌ Remove fields from v1
- ❌ Rename v1 fields
- ❌ Change v1 response structure

**Instead, add `/api/v2/` for new features!**

---

## 📊 **Success Metrics**

### **Track These:**
```markdown
1. Version Distribution:
   - v1 requests: 95%
   - v2 requests: 5%
   - Target: Gradual migration over 6 months

2. Deprecated Usage:
   - v1 (deprecated) requests: 2%
   - Target: 0% within 6 months of deprecation

3. Error Rates by Version:
   - v1 errors: <1%
   - v2 errors: <2% (acceptable for new version)

4. Migration Progress:
   - Users on v1: 10,000
   - Users on v2: 500
   - Target: 100% on v2 by month 6
```

---

## 🎉 **Benefits**

### **What You Get:**

1. **Safe Evolution** ✅
   - Add features without breaking users
   - Deprecate old endpoints gradually
   - No surprise breakages

2. **Professional Image** ✅
   - Shows long-term thinking
   - Enterprise buyers expect this
   - Investors notice this

3. **Flexibility** ✅
   - Support multiple API versions
   - A/B test new designs
   - Gradual rollout of changes

4. **Backward Compatibility** ✅
   - Old mobile apps keep working
   - Third-party integrations don't break
   - Users migrate when ready

---

## 🔥 **Bottom Line**

**You now have production-grade API versioning that:**
- ✅ Allows free iteration during beta
- ✅ Enables safe evolution after launch
- ✅ Supports gradual migrations
- ✅ Prevents breaking changes
- ✅ Adds professional polish

**This is the same system used by:**
- Stripe (industry leader)
- GitHub (rock-solid)
- Twilio (developer-friendly)

**You're in good company!** 🚀

---

## 📞 **Support**

### **Questions:**
- How do I add a new version? → See "Adding v2 Endpoint" section
- Can I change v1 during beta? → YES! Beta = experimental
- When do I enforce versioning? → At public launch
- How long should I support old versions? → 12-18 months minimum

**You're now enterprise-ready for API evolution!** 💪

