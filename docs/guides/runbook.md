# Operations Runbook - Forge Backend

This runbook provides procedures for common operational tasks and incident response.

## Table of Contents

- [Deployment](#deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Incident Response](#incident-response)
- [Maintenance](#maintenance)

## Deployment

### Production Deployment

1. **Pre-deployment Checklist**
   - [ ] All tests passing
   - [ ] Environment variables configured
   - [ ] Database migrations applied
   - [ ] Secrets configured
   - [ ] Monitoring configured

2. **Deploy with Gunicorn**

```bash
gunicorn forge.server.listen:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:3000 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile -
```

3. **Health Check**

```bash
curl http://localhost:3000/api/monitoring/health
```

### Environment Variables

Required for production:

```bash
# Server
WORKERS=4
HOST=0.0.0.0
PORT=3000

# Authentication
AUTH_ENABLED=true
JWT_SECRET=<strong-secret>

# Database
DATABASE_URL=<connection-string>

# Redis
REDIS_URL=redis://localhost:6379

# Security
DOCKER_SECURITY_ENABLED=true
DOCKER_MEMORY_LIMIT=2g
DOCKER_CPU_QUOTA=50000
```

## Monitoring

### Health Checks

**Liveness Probe:**
```bash
curl http://localhost:3000/alive
```

**Readiness Probe:**
```bash
curl http://localhost:3000/api/monitoring/readiness
```

**Health Check:**
```bash
curl http://localhost:3000/api/monitoring/health
```

### Metrics

**Prometheus Metrics:**
```bash
curl http://localhost:3000/api/monitoring/metrics
```

**Expanded Metrics:**
```bash
curl http://localhost:3000/api/monitoring/metrics/expanded
```

### Key Metrics to Monitor

1. **Conversation Metrics**
   - Active conversations
   - Success rate
   - Average duration
   - P95/P99 latency

2. **LLM Metrics**
   - Total calls
   - Success rate
   - Cost per conversation
   - Average latency

3. **API Metrics**
   - Request rate
   - Error rate
   - P95/P99 latency
   - By endpoint

4. **Resource Metrics**
   - Memory usage
   - CPU usage
   - Disk usage
   - Connection count

## Troubleshooting

### Server Won't Start

**Check logs:**
```bash
# Check for errors in logs
tail -f logs/forge.log

# Check system resources
df -h  # Disk space
free -h  # Memory
top  # CPU
```

**Common issues:**
- Port already in use: `lsof -i :3000`
- Database connection failed: Check `DATABASE_URL`
- Redis connection failed: Check `REDIS_URL`

### High Error Rate

1. **Check error logs:**
```bash
grep ERROR logs/forge.log | tail -100
```

2. **Check metrics:**
```bash
curl http://localhost:3000/api/monitoring/metrics/expanded
```

3. **Check resource usage:**
```bash
# Docker containers
docker stats

# System resources
htop
```

### Slow Performance

1. **Check database:**
```bash
# Connection pool status
curl http://localhost:3000/api/monitoring/health

# Slow queries (if enabled)
# Check database logs
```

2. **Check caching:**
```bash
# Redis status
redis-cli ping

# Cache hit rate
curl http://localhost:3000/api/monitoring/metrics | grep cache
```

3. **Check LLM latency:**
```bash
curl http://localhost:3000/api/monitoring/metrics/expanded | jq '.llm.avg_latency_ms'
```

### Memory Leaks

1. **Monitor memory:**
```bash
# Container memory
docker stats

# Process memory
ps aux | grep forge
```

2. **Check for leaks:**
```bash
# Python memory profiler
pip install memory-profiler
python -m memory_profiler your_script.py
```

3. **Restart if needed:**
```bash
# Graceful restart
kill -SIGTERM <pid>
# Wait for graceful shutdown, then restart
```

## Incident Response

### Service Down

1. **Check health:**
```bash
curl http://localhost:3000/api/monitoring/health
```

2. **Check logs:**
```bash
tail -100 logs/forge.log
```

3. **Check system:**
```bash
# Disk space
df -h

# Memory
free -h

# Processes
ps aux | grep forge
```

4. **Restart service:**
```bash
# Graceful restart
systemctl restart forge

# Or manual restart
pkill -f "forge.server"
python -m forge.server
```

### High Error Rate

1. **Identify error type:**
```bash
# Check error codes
grep "error_code" logs/forge.log | sort | uniq -c
```

2. **Check specific errors:**
```bash
# Authentication errors
grep "AUTHENTICATION" logs/forge.log

# Rate limit errors
grep "RATE_LIMIT" logs/forge.log

# Resource quota errors
grep "RESOURCE_QUOTA" logs/forge.log
```

3. **Take action:**
   - **Rate limiting**: Check if legitimate traffic or attack
   - **Resource quota**: Check user quotas and limits
   - **Authentication**: Check JWT secret and token expiration

### Database Issues

1. **Check connection:**
```bash
curl http://localhost:3000/api/monitoring/health | jq '.services.database'
```

2. **Check pool status:**
```python
from forge.storage.db_pool import get_db_pool
pool = get_db_pool()
print(pool.get_pool_status())
```

3. **Common fixes:**
   - Increase pool size
   - Check connection timeout
   - Verify database is running
   - Check network connectivity

### Redis Issues

1. **Check connection:**
```bash
redis-cli ping
```

2. **Check health:**
```bash
curl http://localhost:3000/api/monitoring/health | jq '.services.redis'
```

3. **Common fixes:**
   - Restart Redis
   - Check memory usage: `redis-cli info memory`
   - Clear cache if needed: `redis-cli FLUSHDB`

## Maintenance

### Regular Tasks

**Daily:**
- Monitor error rates
- Check resource usage
- Review logs for anomalies

**Weekly:**
- Review metrics trends
- Check for memory leaks
- Verify backups

**Monthly:**
- Update dependencies
- Review security patches
- Performance optimization review

### Backup Procedures

1. **Database Backup:**
```bash
# PostgreSQL
pg_dump -h localhost -U user database > backup.sql

# SQLite
cp database.db backup.db
```

2. **Configuration Backup:**
```bash
# Environment variables
env > .env.backup

# Configuration files
cp config.toml config.toml.backup
```

### Log Rotation

Configure log rotation in `/etc/logrotate.d/forge`:

```
/var/log/forge/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 user group
}
```

### Performance Tuning

1. **Worker Count:**
```bash
# Formula: (2 × CPU cores) + 1
WORKERS=5  # For 2 CPU cores
```

2. **Connection Pool:**
```bash
DB_POOL_SIZE=20
DB_POOL_MAX_OVERFLOW=10
```

3. **Caching:**
```bash
# Enable Redis for caching
REDIS_URL=redis://localhost:6379
```

## Emergency Contacts

- **On-Call Engineer**: [Contact Info]
- **Database Admin**: [Contact Info]
- **Infrastructure Team**: [Contact Info]

## Escalation Procedures

1. **Level 1**: Check logs and metrics
2. **Level 2**: Restart service
3. **Level 3**: Rollback deployment
4. **Level 4**: Escalate to on-call engineer

