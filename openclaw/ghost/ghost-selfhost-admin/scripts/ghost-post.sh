#!/bin/bash
#
# ghost-post.sh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Create a new Ghost post using existing session
#
# Usage:
#   ./ghost-post.sh --title "My Post" --body "Content..." [options]
#
# Options:
#   --title TEXT        Post title (required)
#   --body TEXT         Post body/content (required, Markdown or HTML)
#   --slug SLUG         URL slug (auto-generated if omitted)
#   --tags TAG1,TAG2    Comma-separated tags
#   --feature-image URL Feature image URL
#   --excerpt TEXT      Short excerpt for preview
#   --publish            Publish immediately (default: draft)
#   --env FILE          Load config from .env (default: .env)
#
# Examples:
#   # Create draft
#   ./ghost-post.sh --title "PostgreSQL Incident" --body "$(cat post.md)"
#
#   # Publish immediately
#   ./ghost-post.sh --title "The One Thing" --body "..." --publish --tags "career,leadership"
#
# Requirements:
#   - ghost-login.sh must have been run first (creates ~/.ghost/session.json)
#   - curl
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/../lib"

# === Load library functions ===
source "$LIB_DIR/config.sh"
source "$LIB_DIR/http.sh"

# === Parse arguments ===
parse_args() {
    local title="" body="" slug="" tags="" feature_image="" excerpt="" publish=false env_file=".env"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --title)        title="$2"; shift 2;;
            --body)         body="$2"; shift 2;;
            --slug)         slug="$2"; shift 2;;
            --tags)         tags="$2"; shift 2;;
            --feature-image) feature_image="$2"; shift 2;;
            --excerpt)      excerpt="$2"; shift 2;;
            --publish)      publish=true; shift;;
            --env)          env_file="$2"; shift 2;;
            *)              echo "Unknown option: $1"; return 1;;
        esac
    done
    
    # Validate required
    if [[ -z "$title" || -z "$body" ]]; then
        echo "❌ Missing required arguments"
        echo "Usage: $0 --title 'Title' --body 'Content' [options]"
        return 1
    fi
    
    # Export for use in main()
    export POST_TITLE="$title"
    export POST_BODY="$body"
    export POST_SLUG="${slug:-}"
    export POST_TAGS="$tags"
    export POST_FEATURE_IMAGE="${feature_image:-}"
    export POST_EXCERPT="${excerpt:-}"
    export POST_PUBLISH=$publish
    export ENV_FILE="$env_file"
}

# === Main post creation ===
main() {
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  📝 Ghost Post Creator                                         ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Load config
    echo "[1/3] Loading configuration..."
    load_env "$ENV_FILE" || true
    validate_config || return 1
    
    # Check session exists
    echo "[2/3] Checking authentication..."
    if [[ ! -f "$GHOST_SESSION_FILE" ]]; then
        echo "❌ No session found. Run './ghost-login.sh' first"
        return 1
    fi
    echo "  ✓ Session found"
    
    # Build post payload
    echo "[3/3] Creating post..."
    
    # Auto-generate slug from title if not provided
    local post_slug="${POST_SLUG:-$(echo "$POST_TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-\+/-/g' | sed 's/^-\|-$//g')}"
    
    local status="draft"
    [[ "$POST_PUBLISH" == "true" ]] && status="published"
    
    # Build JSON payload
    local post_data=$(cat <<EOF
{
  "posts": [{
    "title": "$(echo "$POST_TITLE" | sed 's/"/\\"/g')",
    "slug": "$post_slug",
    "html": "$(echo "$POST_BODY" | sed 's/"/\\"/g' | sed 's/$/\\n/g')",
    "status": "$status"
EOF
)
    
    # Add optional fields
    if [[ -n "$POST_EXCERPT" ]]; then
        post_data+=",\"excerpt\": \"$(echo "$POST_EXCERPT" | sed 's/"/\\"/g')\""
    fi
    if [[ -n "$POST_FEATURE_IMAGE" ]]; then
        post_data+=",\"feature_image\": \"$POST_FEATURE_IMAGE\""
    fi
    
    post_data+="
  }]
}"
    
    # API endpoint
    local api_url="${GHOST_URL}/ghost/api/v5/admin/posts"
    
    # TODO: Extract bearer token from session and add Authorization header
    # For now, rely on cookies from session file
    
    echo "  Creating $status post: $POST_TITLE"
    echo "  Slug: $post_slug"
    
    local response=$(http_request POST "$api_url" "$post_data" || echo "")
    
    # Check result
    if echo "$response" | grep -q "\"id\""; then
        local post_id=$(echo "$response" | grep -oP '"id"\s*:\s*"\K[^"]+' | head -1)
        echo ""
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║  ✅ Post Created Successfully                                  ║"
        echo "╚════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Post ID: $post_id"
        echo "Slug: $post_slug"
        echo "Status: $status"
        echo ""
        echo "View: ${GHOST_URL}/${post_slug}/"
        echo "Edit: ${GHOST_URL}/ghost/#/editor/${post_id}"
        echo ""
        return 0
    else
        echo "❌ Failed to create post"
        echo "Response: $response"
        return 1
    fi
}

# === Run ===
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 --title 'Title' --body 'Content' [--publish] [--tags 'tag1,tag2']"
    echo ""
    echo "Examples:"
    echo "  $0 --title 'My Post' --body 'Post content here...'"
    echo "  $0 --title 'Published Post' --body '...' --publish --tags 'career,fintechs'"
    echo ""
    exit 1
fi

parse_args "$@"
main
