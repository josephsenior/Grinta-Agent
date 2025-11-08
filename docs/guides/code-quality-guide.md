# Code Quality Guide for Contributors

This guide helps you write high-quality code that meets Forge's exceptional standards.

## Quick Reference

### Complexity Ratings
```
✅ A (1-5):   Excellent - Your target
✅ B (6-10):  Good - Acceptable
⚠️ C (11-20): Needs refactoring
❌ D (21-50): Must refactor
🚫 E-F (>50): Blocked
```

### Check Your Code
```bash
# Check specific file
radon cc forge/path/to/your/file.py -s

# Check all your changes
radon cc forge -s | grep "your_function_name"

# Check average complexity
radon cc forge/path/to/your/file.py -a
```

## Writing Low-Complexity Code

### 1. Keep Functions Small and Focused

**❌ Bad: One function does everything**
```python
def process_user_data(user_data):
    """Process user data (complexity 15)."""
    # 50 lines of validation
    if not user_data:
        raise ValueError()
    if 'email' not in user_data:
        raise ValueError()
    if not validate_email(user_data['email']):
        raise ValueError()
    # ... 10 more validation checks
    
    # 30 lines of transformation
    user_data['email'] = user_data['email'].lower()
    user_data['name'] = user_data['name'].strip()
    # ... 10 more transformations
    
    # 20 lines of database operations
    if user_exists(user_data['email']):
        update_user(user_data)
    else:
        create_user(user_data)
    # ... more database logic
    
    return user_data
```

**✅ Good: Break into focused functions**
```python
def _validate_user_data(user_data: dict) -> None:
    """Validate user data (complexity 4)."""
    if not user_data:
        raise ValueError("User data is required")
    if 'email' not in user_data:
        raise ValueError("Email is required")
    if not validate_email(user_data['email']):
        raise ValueError("Invalid email format")

def _transform_user_data(user_data: dict) -> dict:
    """Transform user data (complexity 2)."""
    return {
        'email': user_data['email'].lower(),
        'name': user_data['name'].strip(),
    }

def _save_user_data(user_data: dict) -> None:
    """Save user data to database (complexity 3)."""
    if user_exists(user_data['email']):
        update_user(user_data)
    else:
        create_user(user_data)

def process_user_data(user_data: dict) -> dict:
    """Process user data (complexity 3)."""
    self._validate_user_data(user_data)
    transformed = self._transform_user_data(user_data)
    self._save_user_data(transformed)
    return transformed
```

### 2. Use Guard Clauses

**❌ Bad: Nested conditions**
```python
def process_request(request):
    """Process request (complexity 8)."""
    if request is not None:
        if request.is_valid():
            if request.has_auth():
                if request.user.is_active():
                    # actual processing
                    return process(request)
                else:
                    raise InactiveUserError()
            else:
                raise AuthError()
        else:
            raise ValidationError()
    else:
        raise ValueError()
```

**✅ Good: Early returns**
```python
def process_request(request):
    """Process request (complexity 5)."""
    if request is None:
        raise ValueError("Request is required")
    if not request.is_valid():
        raise ValidationError("Invalid request")
    if not request.has_auth():
        raise AuthError("Authentication required")
    if not request.user.is_active():
        raise InactiveUserError("User is inactive")
    
    return process(request)
```

### 3. Replace Long if-elif Chains with Dictionaries

**❌ Bad: 15+ elif branches**
```python
def get_handler(event_type):
    """Get event handler (complexity 16)."""
    if event_type == 'user_created':
        return handle_user_created
    elif event_type == 'user_updated':
        return handle_user_updated
    elif event_type == 'user_deleted':
        return handle_user_deleted
    # ... 12 more elif branches
    else:
        return handle_unknown
```

**✅ Good: Dictionary dispatch**
```python
def get_handler(event_type):
    """Get event handler (complexity 2)."""
    handlers = {
        'user_created': handle_user_created,
        'user_updated': handle_user_updated,
        'user_deleted': handle_user_deleted,
        # ... more handlers
    }
    return handlers.get(event_type, handle_unknown)
```

### 4. Extract Complex Conditionals

**❌ Bad: Complex boolean logic**
```python
def should_process(user, request, config):
    """Check if should process (complexity 12)."""
    if (user.is_active and user.has_permission('write') and 
        not user.is_suspended and user.verified_email and
        request.is_valid and request.method == 'POST' and
        config.processing_enabled and not config.maintenance_mode and
        time_is_within_window() and quota_not_exceeded()):
        return True
    return False
```

**✅ Good: Extract helper functions**
```python
def _user_can_process(user: User) -> bool:
    """Check if user can process requests (complexity 5)."""
    return (user.is_active and 
            user.has_permission('write') and 
            not user.is_suspended and 
            user.verified_email)

def _request_is_processable(request: Request) -> bool:
    """Check if request can be processed (complexity 3)."""
    return request.is_valid and request.method == 'POST'

def _system_allows_processing(config: Config) -> bool:
    """Check if system allows processing (complexity 4)."""
    return (config.processing_enabled and 
            not config.maintenance_mode and
            time_is_within_window() and 
            quota_not_exceeded())

def should_process(user: User, request: Request, config: Config) -> bool:
    """Check if should process (complexity 4)."""
    return (self._user_can_process(user) and
            self._request_is_processable(request) and
            self._system_allows_processing(config))
```

### 5. Use Strategy Pattern for Type-Based Logic

**❌ Bad: Type checking everywhere**
```python
def handle_event(event):
    """Handle event (complexity 10)."""
    if isinstance(event, UserEvent):
        # 10 lines of user event handling
        pass
    elif isinstance(event, SystemEvent):
        # 10 lines of system event handling
        pass
    elif isinstance(event, ErrorEvent):
        # 10 lines of error event handling
        pass
    # ... more types
```

**✅ Good: Separate handlers**
```python
def _handle_user_event(event: UserEvent) -> None:
    """Handle user event (complexity 3)."""
    # User event handling logic
    pass

def _handle_system_event(event: SystemEvent) -> None:
    """Handle system event (complexity 3)."""
    # System event handling logic
    pass

def _handle_error_event(event: ErrorEvent) -> None:
    """Handle error event (complexity 3)."""
    # Error event handling logic
    pass

def handle_event(event: Event) -> None:
    """Handle event (complexity 2)."""
    handlers = {
        UserEvent: self._handle_user_event,
        SystemEvent: self._handle_system_event,
        ErrorEvent: self._handle_error_event,
    }
    handler = handlers.get(type(event))
    if handler:
        handler(event)
```

## Common Patterns in Forge

### Pattern 1: Validation + Processing + Logging

```python
def _validate_input(data: dict) -> None:
    """Validate input data."""
    if not data:
        raise ValueError("Data required")
    # More validation

def _process_data(data: dict) -> dict:
    """Process data."""
    # Processing logic
    return processed_data

def _log_result(result: dict) -> None:
    """Log processing result."""
    logger.info(f"Processed: {result}")

def process(data: dict) -> dict:
    """Main processing function (complexity 3)."""
    self._validate_input(data)
    result = self._process_data(data)
    self._log_result(result)
    return result
```

### Pattern 2: Multi-Phase Operations

```python
def _phase_1_initialize(context: Context) -> State:
    """Initialize processing (complexity 3)."""
    # Phase 1 logic
    return initial_state

def _phase_2_execute(state: State) -> Result:
    """Execute main logic (complexity 4)."""
    # Phase 2 logic
    return result

def _phase_3_finalize(result: Result) -> Output:
    """Finalize and clean up (complexity 3)."""
    # Phase 3 logic
    return output

def run_pipeline(context: Context) -> Output:
    """Run complete pipeline (complexity 4)."""
    state = self._phase_1_initialize(context)
    result = self._phase_2_execute(state)
    output = self._phase_3_finalize(result)
    return output
```

### Pattern 3: Configuration Validation

```python
def _validate_rate_limits(config: Config) -> list[str]:
    """Validate rate limit config (complexity 3)."""
    errors = []
    if config.rate_limit < 0:
        errors.append("Rate limit must be positive")
    return errors

def _validate_thresholds(config: Config) -> list[str]:
    """Validate threshold config (complexity 3)."""
    errors = []
    if config.threshold < 0 or config.threshold > 1:
        errors.append("Threshold must be 0-1")
    return errors

def _validate_resources(config: Config) -> list[str]:
    """Validate resource config (complexity 3)."""
    errors = []
    if config.max_memory < config.min_memory:
        errors.append("Max memory < min memory")
    return errors

def validate_config(config: Config) -> list[str]:
    """Validate complete configuration (complexity 4)."""
    errors = []
    errors.extend(self._validate_rate_limits(config))
    errors.extend(self._validate_thresholds(config))
    errors.extend(self._validate_resources(config))
    return errors
```

## Testing Low-Complexity Code

### Benefits
- Each helper function can be tested independently
- Tests are simpler and more focused
- Higher code coverage is easier to achieve
- Bugs are easier to isolate

### Example

```python
# Test each helper separately
def test_validate_user_data():
    with pytest.raises(ValueError):
        _validate_user_data({})

def test_transform_user_data():
    result = _transform_user_data({'email': 'TEST@EXAMPLE.COM'})
    assert result['email'] == 'test@example.com'

def test_save_user_data():
    # Test database operations
    pass

# Integration test
def test_process_user_data_integration():
    result = process_user_data({'email': 'test@example.com', 'name': 'John'})
    assert result is not None
```

## Before Submitting Your PR

### Checklist

- [ ] Run complexity check: `radon cc forge/your/file.py -s`
- [ ] All functions are A or B rated (≤ 10 complexity)
- [ ] Added docstrings to all public functions
- [ ] Added type hints to function signatures
- [ ] Wrote unit tests for new functions
- [ ] Ran linters: `ruff check .` and `mypy .`
- [ ] Formatted code: `black .` and `isort .`

### Pre-Commit Hook (Recommended)

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Check complexity of changed Python files
for file in $(git diff --cached --name-only | grep '\.py$'); do
    if radon cc "$file" -s | grep -E " - [C-F] \("; then
        echo "❌ High complexity detected in $file"
        echo "Please refactor before committing"
        exit 1
    fi
done
```

## Resources

- [CODE_QUALITY.md](../CODE_QUALITY.md) - Detailed metrics and standards
- [REFACTORING_CHANGELOG.md](../REFACTORING_CHANGELOG.md) - Refactoring history
- [Development Guide](../development.md) - Development setup
- [Contributing Guide](../../CONTRIBUTING.md) - How to contribute

## Questions?

If you need help refactoring complex code:
1. Check [REFACTORING_CHANGELOG.md](../REFACTORING_CHANGELOG.md) for examples
2. Look at recently refactored functions for patterns
3. Ask in GitHub Discussions
4. Reference this guide for common patterns

---

**Remember:** Simple code is better code. When in doubt, extract a helper function! 🚀

