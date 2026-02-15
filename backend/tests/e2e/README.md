# Forge End-to-End Tests

This directory contains end-to-end tests for the Forge application using Playwright.

## Running the Tests

### Prerequisites

- Python 3.12+
- Poetry
- Node.js
- Playwright

### Environment Variables

Required:

- `GIT_PROVIDER_TOKEN`: Provider token for repository access
- `LLM_MODEL`: Model name (for example: `gpt-4o`)
- `LLM_API_KEY`: API key for the selected model

Optional:

- `LLM_BASE_URL`: Custom model endpoint

### Common Commands

```bash
cd tests/e2e
poetry run pytest test_conversation.py::test_conversation_start -v
poetry run pytest test_multi_conversation_resume.py::test_multi_conversation_resume -v
```

With custom base URL:

```bash
cd tests/e2e
poetry run pytest test_conversation.py::test_conversation_start -v --base-url=http://localhost:12000
```

With visible browser:

```bash
cd tests/e2e
poetry run pytest test_conversation.py::test_conversation_start -v --no-headless --slow-mo=50
poetry run pytest test_multi_conversation_resume.py::test_multi_conversation_resume -v --no-headless --slow-mo=50
```

## Test Descriptions

### Conversation Start Test

Verifies a user can launch a conversation and receive a response.

### Multi-Conversation Resume Test

Verifies conversation continuity by resuming a prior conversation and checking contextual follow-up behavior.

### Local Runtime Test

A separate test (`test_headless_mode_with_echo_no_browser` in `test_local_runtime.py`) that tests the local runtime with a dummy agent in headless mode.

## Troubleshooting

If the tests fail, check the following:

1. Make sure all required environment variables are set
2. Check the logs in `/tmp/Forge-e2e-test.log` and `/tmp/Forge-e2e-build.log`
3. Verify that the Forge application is running correctly
4. Check the Playwright test results in the `test-results` directory
