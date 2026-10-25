#!/bin/bash
# =============================================================================
# Ghost MCP Wrapper Script
# =============================================================================
# This script securely launches the Ghost MCP server by retrieving the API key
# from macOS Keychain instead of storing it in plaintext config files.
#
# SETUP INSTRUCTIONS:
# -------------------
# 1. Store your Ghost Admin API key in macOS Keychain:
#
#    security add-generic-password -s "ghost-admin-api" -a "$USER" -w "YOUR_API_KEY_HERE"
#
#    To get your API key:
#    - Go to Ghost Admin → Settings → Integrations → Add custom integration
#    - Copy the Admin API Key (format: {id}:{secret})
#
# 2. Make this script executable:
#
#    chmod +x /path/to/heartbeat/ghost-mcp/ghost-mcp-wrapper.sh
#
# 3. Add to your Claude Code MCP config (~/.claude.json):
#
#    {
#      "mcpServers": {
#        "ghost": {
#          "command": "/path/to/heartbeat/ghost-mcp/ghost-mcp-wrapper.sh"
#        }
#      }
#    }
#
# 4. Restart Claude Code to load the new MCP server.
#
# USAGE:
# ------
# Once configured, Claude will have access to Ghost tools:
#   - ghost_add_post: Create new blog posts
#   - ghost_edit_post: Update existing posts
#   - ghost_browse_posts: List posts with filters
#   - ghost_browse_tags: List available tags
#   - ghost_add_tag: Create new tags
#
# TO UPDATE THE API KEY:
# ----------------------
# Delete the old key and add a new one:
#
#    security delete-generic-password -s "ghost-admin-api"
#    security add-generic-password -s "ghost-admin-api" -a "$USER" -w "NEW_KEY"
#
# TO VERIFY THE KEY IS STORED:
# ----------------------------
#    security find-generic-password -s "ghost-admin-api" -w
#
# =============================================================================

set -e

# Configuration
export GHOST_API_URL="https://heartbeatchurch.com.au"
export GHOST_API_VERSION="v5.0"

# Retrieve API key from macOS Keychain
GHOST_ADMIN_API_KEY=$(security find-generic-password -s "ghost-admin-api" -w 2>/dev/null)

if [ -z "$GHOST_ADMIN_API_KEY" ]; then
    echo "Error: Ghost Admin API key not found in Keychain." >&2
    echo "Run: security add-generic-password -s \"ghost-admin-api\" -a \"\$USER\" -w \"YOUR_KEY\"" >&2
    exit 1
fi

export GHOST_ADMIN_API_KEY

# Launch the MCP server
exec npx -y @fanyangmeng/ghost-mcp
