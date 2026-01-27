# Production Workspace Permissions

**Status:** ✅ **Resolved** - Docker volumes are now used by default  
**Last Updated:** 2025-01-27

---

## Summary

Production workspace permission issues have been resolved by migrating to Docker named volumes. This document describes the previous issues and the solution.

---

## Previous Issues (Resolved)

### ❌ Problems with Bind Mounts

1. **Data Persistence**: `/tmp/` was ephemeral - data lost on container restart
   - Downloads in `/tmp/.downloads` were lost
   - VSCode settings in `/tmp/.vscode` were lost
   - No automatic copy mechanism existed

2. **Permission Problems**: Workspace mount inherited host permissions
   - If host directory was owned by root, container user (uid 1000) couldn't write
   - Code tried to fix permissions but could fail silently

3. **Scalability**: The `/tmp/` fallback worked but wasn't production-ready
   - Works for single-user development
   - Not suitable for multi-user production environments

---

## Current Solution: Docker Named Volumes

### ✅ How It Works

**Docker volumes are now used by default** for workspace storage:

1. **Automatic Volume Creation**: Each conversation gets its own Docker volume
2. **Permission Handling**: Docker volumes are automatically writable by the container user (uid 1000)
3. **Data Persistence**: Volumes persist across container restarts
4. **Isolation**: Each conversation has its own isolated volume

### Benefits

- ✅ **No Permission Issues**: Docker volumes are automatically writable by the container user
- ✅ **Data Persistence**: Workspace data survives container restarts
- ✅ **Production Ready**: Suitable for multi-user production environments
- ✅ **Cross-Platform**: Works on Windows, Mac, and Linux without host-side permission configuration
- ✅ **Better Isolation**: Each conversation has its own isolated volume

---

## Migration Details

See [Docker Volumes Migration](../architecture/docker-volumes-migration.md) for complete migration details.

### Key Changes

1. **Automatic Volume Creation**: Volumes are created automatically when containers start
2. **Volume Naming**: `forge-workspace-{container_name}`
3. **Volume Labels**: Metadata for management (app, role, container, conversation)
4. **Backward Compatible**: Bind mounts still work if explicitly configured

---

## Configuration

### Default Behavior (No Configuration Needed)

Docker volumes are used by default - no configuration required!

### Custom Configuration

You can still configure custom volumes via `SANDBOX_VOLUMES`:

```bash
# Use named volume
SANDBOX_VOLUMES="volume:my-custom-volume:/workspace:rw"

# Use bind mount (if needed, not recommended for production)
SANDBOX_VOLUMES="/host/path:/workspace:rw"
```

---

## Troubleshooting

### Permission Issues

**Symptom:** `Permission denied when writing to /workspace`

**Solution:**
- This should not happen with Docker volumes
- Verify volume is mounted: `docker inspect <container-name> | grep Mounts`
- Check volume ownership: `docker exec <container> ls -la /workspace`
- Ensure container runs as correct user (uid 1000)

### Volume Not Found

**Symptom:** `Error: No such volume: forge-workspace-<name>`

**Solution:**
- Volume is created automatically on container start
- Check container logs for volume creation errors
- Verify Docker volume driver is available: `docker info | grep Storage`

---

## Related Documentation

- [Docker Volumes Migration](../architecture/docker-volumes-migration.md) - Complete migration guide
- [Runtime Architecture](../architecture.md#runtime--execution-docker-sandbox) - Runtime architecture
- [Production Deployment](../production_deployment.md) - Production deployment guide

---

**Status:** ✅ **Resolved** - Docker volumes eliminate all permission issues

