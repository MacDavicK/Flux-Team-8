#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Find the sibling folder that contains a dev-start.sh
BACKEND_DIR=""
for dir in "$PARENT_DIR"/*/; do
    if [[ -f "${dir}dev-start.sh" && "$dir" != "$SCRIPT_DIR/" ]]; then
        BACKEND_DIR="${dir%/}"
        break
    fi
done

OPENAPI_URL="http://localhost:8000/openapi.json"

echo "Fetching OpenAPI schema from: $OPENAPI_URL"

# Check if the backend is reachable
if ! curl -sf "$OPENAPI_URL" -o /dev/null; then
    echo "Error: could not reach $OPENAPI_URL" >&2
    if [[ -n "$BACKEND_DIR" ]]; then
        BACKEND_NAME="$(basename "$BACKEND_DIR")"
        echo "Make sure the backend is running. You can start it with: ./$BACKEND_NAME/dev-start.sh" >&2
    else
        echo "Make sure the backend is running by executing its dev-start.sh script." >&2
    fi
    exit 1
fi

# Generate TypeScript types
npx openapi-typescript "$OPENAPI_URL" -o "$SCRIPT_DIR/src/types/api.d.ts"
