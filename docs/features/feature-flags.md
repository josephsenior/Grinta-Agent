# Feature Flags

This document describes the feature flag system used to control advanced/proprietary features in Forge.

## Overview

Feature flags allow us to enable or disable advanced features without code changes. This is useful for:

- **Beta Launch**: Disable advanced features for initial launch while keeping them in the codebase
- **Tier Management**: Control which features are available in which subscription tiers
- **Testing**: Enable/disable features for testing without deployment

## Available Feature Flags

### Security Risk Assessment (`security_risk_assessment`)

Security risk assessment for agent actions, identifying potentially dangerous operations before execution.

- **Config Path**: `config.extended.security_risk_assessment.enabled`
- **Default**: `false`
- **Tier**: Pro
- **Description**: Security risk assessment for agent actions

### Custom Runtime Images (`custom_runtime_images`)

Support for custom Docker images for agent runtime environments.

- **Config Path**: `config.extended.custom_runtime_images.enabled`
- **Default**: `false`
- **Tier**: Pro
- **Description**: Custom Docker images for agent runtime

## Configuration

Feature flags are configured in `config.toml`:

```toml
[extended]
security_risk_assessment_enabled = false
custom_runtime_images_enabled = false
```

## Backend Usage

### Python API

```python
from forge.core.features import get_feature_flags, FeatureUnavailableError
from forge.core.config import load_forge_config

config = load_forge_config()
feature_flags = get_feature_flags(config)

# Check if a feature is enabled
if feature_flags.security_risk_assessment_enabled:
    # Use security risk assessment
    pass
```

## Frontend Usage

### React Hook

```typescript
import { useFeatureFlags } from "#/hooks/query/use-feature-flags";

function MyComponent() {
  const { data: featureFlags, isLoading } = useFeatureFlags();
  
  if (isLoading) return <div>Loading...</div>;
  
  if (!featureFlags?.security_risk_assessment?.enabled) {
    return <FeatureComingSoon featureName="Security Risk Assessment" />;
  }
  
  // Render Security UI
}
```

### Badge Component

```typescript
import { FeatureFlagBadge } from "#/components/features/feature-flag-badge";

function FeatureCard({ feature }) {
  return (
    <div>
      <h3>{feature.name}</h3>
      <FeatureFlagBadge feature={feature} />
    </div>
  );
}
```

### API Client

```typescript
import { getFeatureFlags } from "#/api/features";

const flags = await getFeatureFlags();
```

## API Endpoint

### GET `/api/v1/features`

Returns feature flags status for frontend consumption.

**Response**:

```json
{
  "parallel_execution": {
    "enabled": false,
    "coming_soon": true,
    "tier": "pro",
    "description": "Parallel agent execution"
  }
}
```

## Error Handling

When a disabled feature is accessed:

1. **Backend**: Raises `FeatureUnavailableError` with a user-friendly message
2. **API Routes**: Returns HTTP 403 with error details
3. **Frontend**: Shows "Coming Soon" UI component

## Testing

To test with features enabled/disabled:

1. Update `config.toml` with desired flag values
2. Restart the backend server
3. Test feature access through API or UI

## Roadmap

### Current Status (Beta Launch)

- ✅ Parallel Execution: Disabled (Coming Soon)

### Future Plans

- **Pro Tier Launch**: Enable features for Pro tier subscribers
- **License-Based**: Add license validation for feature access
- **Per-User Flags**: Support user-specific feature flags
- **A/B Testing**: Use feature flags for A/B testing

## Implementation Details

### Backend Architecture

- **Module**: `backend/forge/core/features.py`
- **Exception**: `FeatureUnavailableError`
- **Class**: `FeatureFlags`
- **Global Instance**: Managed via `get_feature_flags()`

### Frontend Architecture

- **API Client**: `frontend/src/api/features.ts`
- **React Hook**: `frontend/src/hooks/query/use-feature-flags.ts`
- **UI Components**: `frontend/src/components/features/feature-flag-badge.tsx`
- **API Endpoint**: `backend/forge/server/routes/features.py`

## Notes

- Feature flags default to `False` if not explicitly set in config
- Feature flags are read at startup and cached
- Changes to `config.toml` require server restart
- Feature flags are backward compatible (missing config values default to disabled)
- All advanced features are part of the Pro tier

