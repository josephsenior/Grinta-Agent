# Use Case: Building a Web Application

Complete guide to building a full-stack web application with Forge.

## Overview

This guide walks through building a complete web application using Forge's agents. We'll build a task management application with:
- REST API backend
- React frontend
- Database integration
- Authentication
- Real-time updates

## Step 1: Project Planning

### Define Requirements

Start by defining what you want to build:

```
I want to build a task management application with the following features:
- User authentication (login/register)
- Create, read, update, delete tasks
- Task categories and tags
- Due dates and priorities
- Search and filtering
- Real-time updates
```

### Break Down into Steps

Use MetaSOP to break this down:

```
Break this project into development steps:
1. Database schema design
2. REST API endpoints
3. Authentication system
4. Frontend components
5. Real-time WebSocket integration
6. Testing
```

## Step 2: Database Schema

### Design the Schema

Ask the agent to design the database:

```
Design a database schema for a task management app with:
- Users table (id, email, password_hash, created_at)
- Tasks table (id, user_id, title, description, category, priority, due_date, completed, created_at)
- Categories table (id, name, color)
- Tags table (id, name)
- TaskTags junction table (task_id, tag_id)
```

### Generate Migration

```
Generate SQL migration files for the schema above.
Include:
- CREATE TABLE statements
- Indexes for performance
- Foreign key constraints
```

## Step 3: REST API Backend

### Create API Structure

```
Create a REST API structure for the task management app:
- POST /api/auth/register - User registration
- POST /api/auth/login - User login
- GET /api/tasks - List user's tasks
- POST /api/tasks - Create new task
- GET /api/tasks/:id - Get task details
- PUT /api/tasks/:id - Update task
- DELETE /api/tasks/:id - Delete task
- GET /api/categories - List categories
- GET /api/tags - List tags
```

### Implement Endpoints

```
Implement the REST API endpoints using FastAPI.
Include:
- Request/response models
- Authentication middleware
- Error handling
- Input validation
- Database queries
```

## Step 4: Authentication

### Implement Authentication

```
Implement JWT-based authentication:
- User registration with password hashing
- User login with token generation
- Token validation middleware
- Password reset functionality
```

### Secure Endpoints

```
Add authentication middleware to protect API endpoints.
Only authenticated users should access:
- Task CRUD operations
- User profile
- Settings
```

## Step 5: Frontend Components

### Create React Components

```
Create React components for the task management app:
- Login/Register forms
- Task list view
- Task detail view
- Task creation/edit form
- Category and tag selectors
- Search and filter controls
```

### State Management

```
Set up Redux store for:
- User authentication state
- Tasks list
- Categories and tags
- UI state (modals, filters)
```

## Step 6: Real-time Updates

### WebSocket Integration

```
Implement WebSocket integration for real-time updates:
- Task creation notifications
- Task update notifications
- Task deletion notifications
- User activity updates
```

### Frontend WebSocket Client

```
Create WebSocket client in React:
- Connect to WebSocket server
- Listen for task updates
- Update UI in real-time
- Handle connection errors
```

## Step 7: Testing

### Backend Tests

```
Write comprehensive tests for:
- API endpoints
- Authentication
- Database operations
- Error handling
```

### Frontend Tests

```
Write tests for:
- Component rendering
- User interactions
- State management
- API integration
```

## Step 8: Deployment

### Production Configuration

```
Configure the application for production:
- Environment variables
- Database connection pooling
- Caching strategy
- Security headers
- Rate limiting
```

### Deployment Steps

```
Create deployment guide:
- Docker containerization
- Database migration
- Environment setup
- Monitoring configuration
```

## Example: Complete Task API

Here's an example of what the agent might generate:

```python
# app/api/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models import Task, User
from app.schemas import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tasks for the current user."""
    tasks = db.query(Task).filter(Task.user_id == current_user.id).all()
    return tasks

@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task."""
    db_task = Task(**task.dict(), user_id=current_user.id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    for key, value in task_update.dict(exclude_unset=True).items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}
```

## Best Practices

### 1. Start Simple

Begin with basic CRUD operations, then add advanced features.

### 2. Test Incrementally

Test each feature as you build it, don't wait until the end.

### 3. Use Type Safety

Use TypeScript for the frontend and type hints for Python backend.

### 4. Document APIs

Document your API endpoints with OpenAPI/Swagger.

### 5. Handle Errors

Implement comprehensive error handling and user-friendly error messages.

## Next Steps

- [Refactoring Legacy Code](02-refactor-legacy.md) - Modernize existing applications
- [API Development](03-api-development.md) - Build robust APIs
- [Best Practices](../guides/best-practices.md) - Development guidelines

## Summary

You've learned how to:
- ✅ Plan a complete web application
- ✅ Design database schemas
- ✅ Build REST APIs
- ✅ Implement authentication
- ✅ Create frontend components
- ✅ Add real-time features
- ✅ Test and deploy

Ready to build your own application!

