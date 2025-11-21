#!/bin/bash
#
# Generate TypeScript types from OpenAPI spec
#
# This script:
# 1. Starts the backend server
# 2. Fetches the OpenAPI spec
# 3. Generates TypeScript types
# 4. Saves to frontend/src/types/api-generated.ts
#
# Usage:
#   ./scripts/generate-api-types.sh

set -e

echo "🚀 Generating TypeScript types from OpenAPI spec..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend is running
if ! curl -s http://localhost:3000/api/monitoring/health > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend not running. Please start it first:${NC}"
    echo "   poetry run python -m Forge.server.listen"
    exit 1
fi

echo "✅ Backend is running"

# Install openapi-typescript if not installed
if ! command -v openapi-typescript &> /dev/null; then
    echo "📦 Installing openapi-typescript..."
    cd frontend
    npm install -D openapi-typescript
    cd ..
fi

# Fetch OpenAPI spec
echo "📥 Fetching OpenAPI spec from http://localhost:3000/openapi.json..."
curl -s http://localhost:3000/openapi.json > /tmp/forge-openapi.json

# Verify spec is valid JSON
if ! jq empty /tmp/forge-openapi.json 2>/dev/null; then
    echo -e "${YELLOW}❌ Invalid OpenAPI spec. Check backend logs.${NC}"
    exit 1
fi

echo "✅ OpenAPI spec fetched successfully"

# Generate TypeScript types
echo "🔨 Generating TypeScript types..."
cd frontend
npx openapi-typescript /tmp/forge-openapi.json \
    --output src/types/api-generated.ts \
    --export-type \
    --path-params-as-types

echo -e "${GREEN}✅ TypeScript types generated successfully!${NC}"
echo "   → frontend/src/types/api-generated.ts"
echo ""
echo "Usage in your code:"
echo "   import type { paths, components } from '#/types/api-generated';"
echo "   type SettingsResponse = components['schemas']['GETSettingsModel'];"
echo ""
echo -e "${GREEN}Done! 🎉${NC}"

