# Changelog

All notable changes to Forge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive FAQ documentation
- Tutorial section with step-by-step guides
- Quick reference guide
- Expanded code examples and recipes
- **File Editing System Architecture:** Two-layer design separating agent-level (Ultimate Editor) and runtime-level (FileEditor) operations
- **Production-Grade FileEditor:** Custom implementation replacing external dependencies with transaction support, atomic writes, and comprehensive error handling
- **Organized Scripts Directory:** Scripts organized into logical subdirectories (database/, setup/, dev/, verify/, build/)
- **Script Documentation:** README files for each script category

### Changed
- **Agent Hub Unification:** All agents consolidated into `backend/forge/agenthub/` (previously split between `backend/agenthub/` and `backend/forge/agenthub/`)
- **Scripts Reorganization:** Scripts moved from flat structure to organized subdirectories
- **Codebase Statistics Updated:** 191,955 lines (110K backend + 82K frontend), 541 Python files, 763 frontend files
- **Documentation Updated:** All references updated to reflect current project structure
- **Migrated from `Forge_aci` to custom FileEditor implementation**
  - Removed external dependency on `Forge_aci` package
  - Implemented production-grade `FileEditor` for runtime file I/O
  - Clear separation: Ultimate Editor (agent-level) uses FileEditor (runtime-level)
  - Better integration with Forge architecture
  - Full control over implementation and features
- **Renamed all "OH" prefixes to "Forge" branding**
  - `OHEditor` → `FileEditor`
  - `OH_ACI` → `FILE_EDITOR` enum
  - Socket.IO events: `oh_event` → `forge_event`
  - Environment variables: `OH_*` → `FORGE_*`
  - Version tags: `oh_v*` → `forge_v*`
- **Migrated from bind mounts to Docker volumes for workspace storage**
  - Removed `WORKSPACE_MOUNT_PATH` environment variable from docker-compose.yml
  - Runtime containers now use Docker named volumes by default
  - Each conversation gets its own isolated volume (`forge-workspace-<container-name>`)
  - Eliminates permission issues (container user owns volumes automatically)
  - Better isolation and security (no host filesystem access)
  - Cross-platform compatible (works identically on Linux, macOS, Windows)
  - Production-grade reliability with automatic volume creation
  - See [Docker Volumes Migration Guide](./architecture/docker-volumes-migration.md) for details

## [1.0.0] - 2024-12-XX

### Added
- **Ultimate Editor**: Structure-aware code editing with Tree-sitter (45+ languages)
- **30+ LLM Providers**: Support for 200+ models via unified API
- **Production Infrastructure**: Circuit breakers, monitoring, cost quotas
- **Comprehensive Testing**: 113,880+ lines of test code (5,073+ test cases)
- **REST API**: 31 route modules covering all platform features
- **WebSocket API**: Real-time communication via Socket.IO
- **Python SDK**: Backend integration library
- **TypeScript SDK**: Frontend integration library
- **Monitoring**: Prometheus + Grafana with 3 dashboards
- **Security**: Docker sandboxing, JWT authentication, encrypted secrets
- **Memory System**: Persistent memory with vector store integration
- **Cost Tracking**: Dollar-based quotas and spending limits

### Changed
- Refactored agent controller for better modularity
- Improved error handling with comprehensive recovery strategies
- Enhanced monitoring with 30+ Prometheus metrics
- Optimized code quality: 0% high-complexity functions

### Removed
- **Prompt Optimization**: Removed prompt optimization, tool optimization, and related routing/documentation
- **AgentDelegateAction**: Removed agent delegation functionality to simplify the core architecture
- **gRPC Event Service**: Replaced gRPC-based event service with a simplified in-process adapter to reduce complexity
- **Obsolete Documentation**: Removed multiple outdated documentation files and references to legacy features

### Fixed
- Fixed critical server startup issues related to event service initialization
- Resolved multiple test failures caused by obsolete feature references
- Cleaned up unused dependencies and backup files in the codebase
- Improved core unit test stability by removing flaky integration tests for deprecated features

## [0.9.0] - 2024-11-XX

### Added
- Beta launch preparation
- UI polish and mobile optimization
- Enhanced error messages
- Improved documentation

### Changed
- Temporarily disabled some advanced UI features for beta
- Improved frontend performance
- Enhanced user experience

## [0.8.0] - 2024-10-XX

### Added
- Authentication system (JWT)
- User management
- Billing integration
- Analytics dashboard

### Changed
- Migrated to FastAPI from Flask
- Improved API structure
- Enhanced security

## [0.7.0] - 2024-09-XX

### Added
- Enhanced memory system

### Changed
- Refactored agent architecture
- Enhanced context management

## [0.6.0] - 2024-08-XX

### Added
- Ultimate Editor with Tree-sitter
- Atomic refactoring
- Structure-aware editing
- Anti-hallucination system

### Changed
- Improved code editing accuracy
- Enhanced refactoring capabilities
- Better error detection

## [0.5.0] - 2024-07-XX

### Added
- Circuit breaker implementation
- Comprehensive error recovery
- Retry logic with exponential backoff
- Monitoring infrastructure

### Changed
- Improved reliability
- Enhanced error handling
- Better observability

## [0.4.0] - 2024-06-XX

### Added
- Multiple LLM provider support
- Provider abstraction layer
- Cost tracking
- Rate limiting

### Changed
- Unified LLM interface
- Improved provider management
- Enhanced cost monitoring

## [0.3.0] - 2024-05-XX

### Added
- Docker runtime sandboxing
- Security enhancements
- File system isolation
- Resource quotas

### Changed
- Improved security posture
- Better sandbox isolation
- Enhanced resource management

## [0.2.0] - 2024-04-XX

### Added
- Basic agent functionality
- Code execution
- File operations
- Terminal interface

### Changed
- Initial agent implementation
- Basic runtime support

## [0.1.0] - 2024-03-XX

### Added
- Initial release
- Basic architecture
- Core components
- Foundation for future development

---

## Version History Summary

- **v1.0.0**: Production-ready release with comprehensive features
- **v0.9.0**: Beta launch preparation
- **v0.8.0**: Authentication and user management
- **v0.7.0**: Agent architecture and memory enhancements
- **v0.6.0**: Advanced code editing
- **v0.5.0**: Reliability improvements
- **v0.4.0**: Multi-provider support
- **v0.3.0**: Security enhancements
- **v0.2.0**: Basic agent functionality
- **v0.1.0**: Initial release

## Upgrade Guide

### From v0.9.0 to v1.0.0

1. Update dependencies:
```bash
poetry update
cd frontend && pnpm update
```

2. Review breaking changes in API
3. Update environment variables if needed
4. Run database migrations (if applicable)

### From v0.8.0 to v0.9.0

1. Update authentication configuration
2. Review new API endpoints
3. Update frontend dependencies

See [Migration Guides](migration/) for detailed upgrade instructions.

## Deprecations

### v1.0.0
- None

### v0.9.0
- Legacy authentication endpoints (use `/api/auth` instead)

## Security Advisories

See [Security Policy](security.md) for current security status and advisories.

---

For detailed release notes, see [Releases](https://github.com/yourusername/Forge/releases).


