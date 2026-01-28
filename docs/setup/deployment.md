# Production Deployment

This guide covers deploying Forge in production environments.

## Prerequisites

- Docker and Docker Compose
- Reverse proxy (nginx, traefik, etc.)
- SSL certificate
- Database (optional, defaults to SQLite)

## Docker Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Forge/Forge.git
   cd Forge
   ```

2. **Configure environment:**
   ```bash
   cp config.template.toml config.production.toml
   # Edit config.production.toml with production settings
   ```

3. **Set environment variables:**
   ```bash
   export FORGE_API_KEY="your-api-key"
   export FORGE_ENVIRONMENT="production"
   # Legacy: FORGE_API_KEY and FORGE_ENVIRONMENT also supported
   ```

4. **Build and run:**
   ```bash
   docker-compose up -d
   ```

## Performance Optimization

### Warm Runtime Pool

Reduce cold-starts by enabling reusable sandboxes and tuning per-key policies:

```toml
[runtime_pool]
enabled = true

  # Policy key format typically includes runtime kind and repo selector
  # Example: "docker|repo:*" applies to all docker runtimes
  [runtime_pool.policies."docker|repo:*"]
  max_size = 4        # max warm entries for this key
  ttl_seconds = 900   # reclaim idle entries after 15 minutes

  # Another example policy
  [runtime_pool.policies."local|repo:*"]
  max_size = 1
  ttl_seconds = 300
```

### Resource Limits

```toml
[core]
max_budget_per_task = 1.0  # USD per task
max_iterations = 100
```

## Scaling

### Horizontal Scaling

- Run multiple instances behind a load balancer
- Use shared database for persistence
- Configure session affinity

### Vertical Scaling

- Increase CPU/memory limits
- Use GPU instances for ML workloads
- Optimize container resources

## Security

### Network Security

- Run behind reverse proxy with SSL
- Use internal networking for services
- Restrict API access with authentication

### Data Security

- Encrypt sensitive configuration
- Use secure API keys
- Enable security analyzer

```toml
[security]
enable_security_analyzer = true
confirmation_mode = true
```

## Monitoring

### Health Checks

- Container health checks
- Application health endpoints
- Runtime monitoring

### Logging

```toml
[core]
save_trajectory_path = "/logs/trajectories"
```

### Metrics

- Track usage and performance
- Monitor costs
- Alert on failures

## Backup and Recovery

- Backup configuration files
- Backup database (if using external DB)
- Backup trajectories/logs

## Troubleshooting

### Common Issues

- **Slow startup:** Check warm runtime pool configuration and adjust `max_size`/`ttl_seconds`
- **Memory issues:** Adjust resource limits
- **API errors:** Verify API keys and network connectivity
- **Container crashes:** Check logs and resource usage

