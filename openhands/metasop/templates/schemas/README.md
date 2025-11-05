# MetaSOP JSON Schema Documentation

## 📋 **Overview**

This directory contains JSON Schema definitions for all MetaSOP agent artifacts. These schemas ensure data integrity, type safety, and validation across the entire MetaSOP system.

---

## 🎯 **Purpose**

**JSON Schema validation provides:**

1. ✅ **Data Integrity** - Ensures artifacts conform to expected structure
2. ✅ **Type Safety** - Validates field types and formats
3. ✅ **Documentation** - Schemas serve as living documentation
4. ✅ **Early Error Detection** - Catches issues before they reach the frontend
5. ✅ **IDE Support** - Enables autocomplete and validation in editors

---

## 📁 **Schema Files**

| File | Agent Role | Description |
|------|-----------|-------------|
| `pm_spec.schema.json` | Product Manager | User stories, acceptance criteria, assumptions, scope |
| `architect.schema.json` | Architect | Design docs, APIs, decisions, database schema, tech stack |
| `engineer.schema.json` | Engineer | Implementation plans, file structures, setup commands |
| `qa.schema.json` | QA | Test results, coverage, security findings, performance |
| `designer.schema.json` | UI Designer | Page layouts, accessibility, design tokens, mobile considerations |
| `pm_approval.schema.json` | Product Manager (Approval) | PM approval after QA |

---

## 🔧 **Using the Schemas**

### **1. Backend Validation (Python)**

```python
from openhands.metasop.schema_validator import validate_artifact

# Validate an artifact
artifact = {
    "user_stories": [
        {
            "id": "US-001",
            "title": "User Login",
            "story": "As a user I want to login",
            "priority": "high"
        }
    ],
    "acceptance_criteria": [
        "User can enter credentials",
        "System validates input"
    ]
}

is_valid, errors, warnings = validate_artifact(artifact, "Product Manager")

if is_valid:
    print("✅ Artifact is valid!")
else:
    print("❌ Validation failed:")
    for error in errors:
        print(f"  - {error}")
```

### **2. Frontend TypeScript Types**

TypeScript interfaces in `frontend/src/types/metasop-artifacts.ts` match these schemas:

```typescript
import type { PMSpecArtifact } from '@/types/metasop-artifacts';

const artifact: PMSpecArtifact = {
  user_stories: [
    {
      id: 'US-001',
      title: 'User Login',
      priority: 'high',
      // TypeScript will warn if types don't match!
    }
  ],
  acceptance_criteria: [...]
};
```

### **3. Schema Validation in Event Emission**

```python
from openhands.metasop.SCHEMA_INTEGRATION_EXAMPLE import EnhancedMetaSOPEventEmitter

emitter = EnhancedMetaSOPEventEmitter(
    emit_callback=my_callback,
    enable_validation=True,
    strict_validation=False  # Set True to fail on validation errors
)

# Artifact will be validated automatically
emitter.emit_step_complete(
    step_id="step_001",
    role="Product Manager",
    artifact=my_artifact
)
```

---

## 📖 **Schema Structure**

### **Common Schema Elements**

All schemas follow JSON Schema Draft-07 specification and include:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://forge.ai/schemas/metasop/[name].json",
  "title": "Human-readable title",
  "description": "Detailed description of the schema",
  "type": "object",
  "required": ["field1", "field2"],
  "properties": {
    "field1": {
      "type": "string",
      "description": "What this field represents",
      "minLength": 10
    }
  },
  "examples": [
    {
      "field1": "Example value"
    }
  ]
}
```

### **Schema Features**

1. **Type Validation** - `type`, `enum`, `format`
2. **String Constraints** - `minLength`, `maxLength`, `pattern`
3. **Numeric Constraints** - `minimum`, `maximum`
4. **Array Constraints** - `minItems`, `maxItems`, `uniqueItems`
5. **Required Fields** - `required` array
6. **Nested Objects** - `$ref` and `definitions`
7. **Examples** - Complete example artifacts

---

## 📚 **Schema Details**

### **1. Product Manager Schema (`pm_spec.schema.json`)**

**Required Fields:**
- `user_stories` - Array of user stories (structured or strings)
- `acceptance_criteria` - Array of acceptance criteria

**Enhanced Fields:**
- `assumptions` - Explicit assumptions made
- `out_of_scope` - Features excluded from scope
- `ui_multi_section` - Whether feature has multiple UI sections
- `ui_sections` - Number of UI sections

**User Story Structure:**
```json
{
  "id": "US-001",
  "title": "Short descriptive title",
  "story": "As a [user] I want [feature] so that [benefit]",
  "description": "Detailed context",
  "priority": "critical|high|medium|low",
  "story_points": 5,
  "estimated_complexity": "small|medium|large",
  "user_value": "Why this matters to users",
  "dependencies": ["US-002"],
  "acceptance_criteria": ["Criterion 1", "Criterion 2"]
}
```

---

### **2. Architect Schema (`architect.schema.json`)**

**Required Fields:**
- `design_doc` - Comprehensive design document (markdown)
- `apis` - Array of API endpoints
- `decisions` - Architectural decisions
- `next_tasks` - Tasks for engineering team

**Enhanced Fields:**
- `database_schema` - Complete database design
- `technology_stack` - Tech choices (frontend, backend, database)
- `integration_points` - External services
- `security_considerations` - Security measures
- `scalability_approach` - Scaling strategy

**API Endpoint Structure:**
```json
{
  "path": "/api/v1/users",
  "method": "GET",
  "description": "Retrieve all users",
  "request_schema": {},
  "response_schema": {},
  "auth_required": true,
  "rate_limit": "100 requests/minute"
}
```

**Database Table Structure:**
```json
{
  "name": "users",
  "description": "User accounts",
  "columns": [
    {
      "name": "id",
      "type": "UUID",
      "constraints": ["PRIMARY KEY"],
      "description": "Unique user identifier"
    }
  ],
  "indexes": [
    {
      "columns": ["email"],
      "type": "btree",
      "reason": "Fast email lookups"
    }
  ],
  "relationships": [
    {
      "type": "one-to-many",
      "from": "id",
      "to": "posts.user_id",
      "description": "User can have many posts"
    }
  ]
}
```

---

### **3. Engineer Schema (`engineer.schema.json`)**

**Required Fields:**
- `artifact_path` - Path to main deliverable
- `tests_added` - Whether tests were added
- `run_results` - Setup/test/dev commands

**Enhanced Fields:**
- `file_structure` - Complete recursive file tree
- `implementation_plan` - Multi-phase development plan
- `files`/`file_changes`/`components` - Alternative file representations

**File Structure (Recursive):**
```json
{
  "name": "src",
  "type": "folder",
  "description": "Source code root",
  "children": [
    {
      "name": "components",
      "type": "folder",
      "description": "React components",
      "children": [
        {
          "name": "Button.tsx",
          "type": "file",
          "description": "Reusable button component"
        }
      ]
    }
  ]
}
```

---

### **4. QA Schema (`qa.schema.json`)**

**Required Fields:**
- `ok` - Overall QA status (boolean)
- `tests` - Test statistics or detailed results

**Enhanced Fields:**
- `test_results` - Detailed test scenarios with categories
- `coverage` - Code coverage metrics
- `coverage_delta` - Coverage change
- `security_findings` - Security vulnerabilities
- `performance_metrics` - Performance test results
- `lint` - Linting results

**Test Result Structure:**
```json
{
  "name": "User authentication flow",
  "status": "passed|failed|skipped",
  "type": "unit|integration|e2e|performance|security",
  "category": "authentication|api|ui|security|performance",
  "priority": "critical|high|medium|low",
  "duration": 250,
  "failure_reason": "Why it failed (if failed)"
}
```

**Security Finding Structure:**
```json
{
  "severity": "critical|high|medium|low|info",
  "vulnerability": "SQL Injection",
  "description": "Detailed description",
  "affected_endpoints": ["/api/login"],
  "remediation": "Use parameterized queries",
  "cve": "CVE-2024-12345"
}
```

---

### **5. UI Designer Schema (`designer.schema.json`)**

**Enhanced Fields:**
- `layout_plan` - Page layouts and component hierarchy
- `accessibility` - WCAG compliance checklist
- `design_tokens` - Design system tokens
- `risks` - Design risks and mitigations
- `mobile_considerations` - Mobile-specific decisions
- `performance_budget` - Performance targets

**Page Layout Structure:**
```json
{
  "name": "Dashboard",
  "route": "/dashboard",
  "description": "Main user dashboard",
  "layout_type": "dashboard|content|form|landing|list|detail",
  "components": [
    {
      "name": "TaskSummaryCard",
      "type": "Card",
      "purpose": "Display quick stats",
      "states": ["default", "loading", "error"],
      "accessibility_notes": "Use ARIA labels"
    }
  ],
  "responsive_breakpoints": {
    "mobile": "Single column",
    "tablet": "2-column grid",
    "desktop": "3-column with sidebar"
  }
}
```

**Accessibility Specification:**
```json
{
  "wcag_level": "A|AA|AAA",
  "checklist": [
    {
      "criterion": "1.4.3",
      "requirement": "Contrast (Minimum)",
      "implementation": "4.5:1 contrast ratio",
      "status": "required|recommended|optional"
    }
  ],
  "keyboard_navigation": {
    "tab_order": "Logo → Nav → Content → Footer",
    "shortcuts": ["Ctrl+K for search"],
    "focus_indicators": "2px blue outline"
  }
}
```

---

## 🔍 **Validation Levels**

### **1. Strict Validation (Recommended for Production)**

```python
validator = SchemaValidator()
is_valid, errors, warnings = validator.validate(
    artifact,
    role="Product Manager",
    raise_on_error=True  # Will raise exception on failure
)
```

### **2. Lenient Validation (Development)**

```python
is_valid, errors, warnings = validate_artifact(
    artifact,
    role="Product Manager",
    raise_on_error=False  # Log errors but don't fail
)

# Continue processing even if validation fails
if not is_valid:
    logger.warning(f"Validation failed: {errors}")
```

### **3. Validation with Suggestions**

```python
is_valid, errors, warnings, suggestions = validate_artifact_with_suggestions(
    artifact,
    role="Product Manager"
)

print(f"Errors: {len(errors)}")
print(f"Warnings: {len(warnings)}")
print(f"Suggestions: {suggestions}")
```

---

## 🚀 **Integration Guide**

### **Step 1: Install Dependencies**

```bash
pip install jsonschema
```

### **Step 2: Import Validator**

```python
from openhands.metasop.schema_validator import (
    validate_artifact,
    validate_artifact_with_suggestions,
    get_validator
)
```

### **Step 3: Validate in Event Emitter**

```python
# In event emitter
if artifact:
    is_valid, errors, warnings = validate_artifact(artifact, role)
    if not is_valid:
        logger.error(f"Artifact validation failed: {errors}")
        # Optionally fail the step or emit warning
```

### **Step 4: Add Validation to Orchestrator**

```python
# In orchestrator after artifact generation
validator = get_validator()
is_valid, errors, warnings = validator.validate(artifact, step_role)

if not is_valid:
    # Log errors
    for error in errors:
        logger.error(f"Validation error: {error}")
    
    # Optionally retry step or continue with warnings
```

---

## 📊 **Validation Metrics**

**Track validation metrics:**

```python
class ValidationMetrics:
    def __init__(self):
        self.total_validations = 0
        self.passed = 0
        self.failed = 0
        self.errors_by_role = {}
    
    def record_validation(self, role: str, is_valid: bool, errors: list):
        self.total_validations += 1
        if is_valid:
            self.passed += 1
        else:
            self.failed += 1
            if role not in self.errors_by_role:
                self.errors_by_role[role] = 0
            self.errors_by_role[role] += len(errors)
    
    def get_success_rate(self) -> float:
        if self.total_validations == 0:
            return 0.0
        return (self.passed / self.total_validations) * 100
```

---

## 🔧 **Troubleshooting**

### **Common Validation Errors**

**1. Missing Required Field**
```
Error: 'user_stories' is a required property
Solution: Add the missing field to your artifact
```

**2. Type Mismatch**
```
Error: 'priority' must be one of ['critical', 'high', 'medium', 'low']
Solution: Use one of the allowed enum values
```

**3. Minimum Length**
```
Error: 'description' should be at least 10 characters
Solution: Provide more detailed descriptions
```

**4. Pattern Mismatch**
```
Error: 'id' does not match pattern '^US-[0-9]+$'
Solution: Use format like 'US-001', 'US-002'
```

### **Debugging Tips**

```python
# Get ALL errors (not just first one)
validator = get_validator()
all_errors = validator.get_all_errors(artifact, role)
for error in all_errors:
    print(f"Error: {error}")

# Validate specific field
from jsonschema import validate
schema = validator.schemas['pm_spec']
validate(artifact['user_stories'], schema['properties']['user_stories'])
```

---

## 🎯 **Best Practices**

1. **✅ DO** - Validate artifacts immediately after generation
2. **✅ DO** - Log all validation errors with context
3. **✅ DO** - Include validation results in event metadata
4. **✅ DO** - Use strict validation in production
5. **✅ DO** - Update schemas when adding new fields

6. **❌ DON'T** - Skip validation in production
7. **❌ DON'T** - Modify artifacts to pass validation (fix the generator)
8. **❌ DON'T** - Ignore validation warnings
9. **❌ DON'T** - Make schemas less strict to pass validation

---

## 📈 **Schema Versioning**

**When updating schemas:**

1. ✅ Add new optional fields
2. ✅ Expand enum values
3. ✅ Relax constraints (increase maxLength, decrease minLength)
4. ⚠️ Making fields required (breaking change)
5. ⚠️ Removing fields (breaking change)
6. ⚠️ Restricting enums (breaking change)

**Breaking changes require:**
- Version bump in `$id` URL
- Migration guide
- Backward compatibility layer

---

## 🆘 **Support**

**For schema-related issues:**

1. Check this README
2. Review examples in schema files
3. Check TypeScript types in `frontend/src/types/metasop-artifacts.ts`
4. Review `schema_validator.py` source code
5. Check validation logs for detailed error messages

---

## 📝 **Schema Maintenance**

**Monthly review checklist:**

- [ ] Ensure schemas match TypeScript types
- [ ] Update examples with real-world data
- [ ] Review validation error logs
- [ ] Add new fields from agent profile enhancements
- [ ] Update documentation
- [ ] Test validation with edge cases
- [ ] Verify schema URLs are accessible

---

## 🎉 **Summary**

**Your MetaSOP schemas provide:**

✅ **Complete validation** for all 5 agent roles  
✅ **100+ validated fields** across all schemas  
✅ **Type safety** with TypeScript integration  
✅ **Examples** in every schema file  
✅ **Comprehensive documentation** (this file!)  
✅ **Production-ready** validation utilities  

**Schema validation ensures** data integrity, catches errors early, and provides excellent developer experience!

---

**Last Updated:** October 24, 2025  
**Schema Version:** 1.0.0  
**JSON Schema Draft:** 7

