---
name: database
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - postgresql
  - postgres
  - mysql
  - mongodb
  - redis
  - database
  - sql
---

# Database Setup

**Core principle:** Simple first. Don't default to Docker unless requested.

## Quick Decision

User mentions database without "docker"? **Ask first:**

```
I can set up [DATABASE] in a few ways:

1. SQLite (Recommended for dev)
   - No installation, works immediately
   
2. Local [DATABASE]
   - You install locally, I create connection code
   
3. Docker Compose
   - Requires Docker installed

Which do you prefer?
```

## Lightweight Alternatives

**PostgreSQL** → SQLite  
**MySQL** → SQLite or MariaDB  
**MongoDB** → NeDB or local MongoDB  
**Redis** → In-memory store or local Redis

## Examples

### SQLite (Node.js)
```javascript
// npm install better-sqlite3
const Database = require('better-sqlite3');
const db = new Database('dev.db');

db.exec(`CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL,
  email TEXT UNIQUE
)`);
```

### PostgreSQL Connection (User Installs)
```javascript
// npm install pg
const { Pool } = require('pg');
const pool = new Pool({
  host: 'localhost',
  database: 'myapp',
  user: 'postgres',
  password: 'password'
});
```

### Docker (If Requested)
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
```

## Rules

**DON'T:**
- Create Docker setup without asking
- Assume Docker is installed

**DO:**
- Present options first
- Recommend simplest (SQLite for dev)
- Verify Docker if chosen
