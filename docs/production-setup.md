# Production Setup Guide

SaaS deployment essentials for Forge.

## Critical Dependencies

### Tree-sitter (Required)
```toml
# pyproject.toml
tree_sitter = "*"
tree-sitter-language-pack = "*"
```

This is Forge's competitive advantage - must always be available.

## Health Check

Startup validation runs automatically on agent init.

**Manual test:**
```bash
python openhands/agenthub/codeact_agent/tools/health_check.py
```

**Expected output:**
```
🏥 FORGE PRODUCTION HEALTH CHECK
============================================================
✅ Ultimate Editor: Tree-sitter is READY
   - Structure-aware editing: ENABLED
   - Language support: 45+ languages
✅ Atomic Refactoring: READY
============================================================
✅ HEALTH CHECK PASSED
============================================================
```

## Deployment Steps

### 1. Build Dependencies
```bash
poetry lock
poetry install
```

### 2. Rebuild Docker
```bash
docker-compose build
```

### 3. Verify
```bash
# Test health check
python openhands/agenthub/codeact_agent/tools/health_check.py

# Check Tree-sitter
docker exec <container> python -c "import tree_sitter; print('OK')"
```

### 4. Deploy
```bash
docker-compose up -d
```

## Health Check Integration

**File:** `openhands/agenthub/codeact_agent/codeact_agent.py`

```python
def _run_production_health_check(self):
    """Validates critical dependencies at startup"""
    run_production_health_check(raise_on_failure=True)
```

**Behavior:**
- Runs on agent initialization
- Raises exception if Tree-sitter missing
- Prevents agent from starting with broken dependencies

## Error Messages

**Production-focused errors with fix instructions:**

```
🚨 CRITICAL: Tree-sitter not available!

PRODUCTION DEPLOYMENT ERROR:
  Tree-sitter should be a required dependency in pyproject.toml.
  Check that Docker image was built with latest dependencies.

Quick fix: pip install tree-sitter tree-sitter-language-pack
Permanent fix: Ensure pyproject.toml has tree_sitter in main dependencies
```

## CI/CD Integration

### GitHub Actions
```yaml
- name: Validate Dependencies
  run: python openhands/agenthub/codeact_agent/tools/health_check.py
```

### Kubernetes Readiness Probe
```yaml
readinessProbe:
  exec:
    command:
    - python
    - -m
    - openhands.agenthub.codeact_agent.tools.health_check
  initialDelaySeconds: 10
  periodSeconds: 30
```

### Docker Healthcheck
```dockerfile
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "from openhands.agenthub.codeact_agent.tools.health_check import run_production_health_check; run_production_health_check()"
```

## Files Modified

**Dependencies:**
- `pyproject.toml` - Tree-sitter required

**Health Check:**
- `openhands/agenthub/codeact_agent/tools/health_check.py` - NEW validation
- `openhands/agenthub/codeact_agent/codeact_agent.py` - Integration

**Error Messages:**
- `openhands/agenthub/codeact_agent/tools/universal_editor.py` - Better errors

## Troubleshooting

**Agent won't start:**
```bash
# Check health check output
docker logs <container> | grep "HEALTH CHECK"

# Verify Tree-sitter
docker exec <container> python -c "import tree_sitter"
```

**Health check fails:**
```bash
# Reinstall dependencies
docker-compose build --no-cache

# Verify pyproject.toml has tree_sitter (not optional)
grep "tree_sitter" pyproject.toml
```

## See Also

- [Forge Improvements](./forge-improvements.md)
- [Ultimate Editor](./ultimate-editor.md)
- [Tool Quick Reference](./tool-quick-reference.md)

