# Tutorial: Your First Agent Conversation

This tutorial will guide you through your first conversation with a Forge agent.

## Prerequisites

- Forge installed and running (see [Getting Started](../getting_started.md))
- At least one LLM provider configured
- A code repository or workspace ready

## Step 1: Start Forge

1. **Start the backend:**
```bash
poetry run python -m forge.server
```

2. **Start the frontend (in a new terminal):**
```bash
cd frontend
pnpm run dev
```

3. **Open your browser:**
Navigate to `http://localhost:5173`

## Step 2: Create Your First Conversation

1. **Click "New Conversation"** or navigate to the home page
2. **Select a repository** (or create a new workspace)
3. **Click "Launch"** to start

## Step 3: Your First Request

Let's start with a simple request to test the agent:

```
Can you read the README.md file and tell me what this project is about?
```

**What happens:**
1. The agent receives your request
2. It reads the README.md file
3. It analyzes the content
4. It responds with a summary

## Step 4: Try Code Editing

Now let's try a code editing task:

```
Can you add a comment to the main function explaining what it does?
```

**What happens:**
1. The agent locates the main function
2. It analyzes the function's purpose
3. It adds an appropriate comment
4. It shows you the changes

## Step 5: Execute Code

Try asking the agent to run some code:

```
Can you run the tests and show me the results?
```

**What happens:**
1. The agent identifies the test command
2. It executes the tests in the sandbox
3. It shows you the test output
4. It summarizes the results

## Understanding Agent Responses

### Agent Thoughts
The agent shows its "thinking" process:
- **Planning**: What it's going to do
- **Actions**: What it's executing
- **Observations**: What it discovered

### Code Changes
When the agent edits code:
- **Green highlights**: Added lines
- **Red highlights**: Removed lines
- **File tree**: Shows which files were modified

### Terminal Output
When the agent runs commands:
- You see the command executed
- You see the output in real-time
- The agent summarizes the results

## Common First Tasks

### 1. Explore the Codebase
```
Can you give me an overview of the project structure?
```

### 2. Fix a Bug
```
I'm getting an error when I run the app. Can you help me debug it?
```

### 3. Add a Feature
```
Can you add a function to calculate the average of a list of numbers?
```

### 4. Refactor Code
```
Can you refactor this function to be more readable?
```

## Tips for Better Conversations

### Be Specific
❌ **Bad:** "Fix the code"
✅ **Good:** "Fix the null pointer exception in the UserService.getUser() method"

### Provide Context
❌ **Bad:** "Make it faster"
✅ **Good:** "The database query in UserRepository.findAll() is taking 5 seconds. Can you optimize it?"

### Break Down Complex Tasks
❌ **Bad:** "Build a complete e-commerce system"
✅ **Good:** "First, let's create the product model and database schema"

### Review Changes
Always review the agent's changes before accepting them. The agent is powerful but not perfect.

## Next Steps

- [Using the Ultimate Editor](04-ultimate-editor.md) - Learn advanced editing features
- [Best Practices](../guides/best-practices.md) - Development guidelines

## Troubleshooting

### Agent Not Responding
- Check that the backend is running
- Verify your LLM API key is configured
- Check the browser console for errors

### Agent Making Mistakes
- Be more specific in your requests
- Break down complex tasks
- Review and correct the agent's work

### Slow Responses
- Check your LLM provider status
- Consider using a faster model
- Review [Performance Tuning](../guides/performance-tuning.md)

## Summary

You've learned:
- ✅ How to start a conversation
- ✅ How to make requests
- ✅ How to read agent responses
- ✅ Tips for better conversations

Ready for more? Continue to the next tutorial!

