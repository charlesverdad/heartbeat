# Ghost MCP Server Setup

MCP (Model Context Protocol) server for interacting with Ghost CMS, allowing Claude to create and manage blog posts.

Uses [@fanyangmeng/ghost-mcp](https://github.com/MFYDev/ghost-mcp) with a wrapper script that securely retrieves API keys from macOS Keychain.

## Quick Setup

### 1. Get Your Ghost Admin API Key

1. Log in to Ghost Admin at https://heartbeatchurch.com.au/ghost
2. Go to **Settings** → **Integrations**
3. Click **Add custom integration**
4. Name it "Claude MCP"
5. Copy the **Admin API Key** (format: `{id}:{secret}`)

### 2. Store the Key in macOS Keychain

```bash
security add-generic-password -s "ghost-admin-api" -a "$USER" -w "YOUR_API_KEY_HERE"
```

### 3. Configure Claude Code

Add to your `~/.claude.json`:

```json
{
  "mcpServers": {
    "ghost": {
      "command": "/Users/charles/work/heartbeat/ghost-mcp/ghost-mcp-wrapper.sh"
    }
  }
}
```

### 4. Restart Claude Code

The Ghost MCP tools will now be available.

## Available Tools

| Tool | Description |
|------|-------------|
| `ghost_browse_posts` | List posts with filters and pagination |
| `ghost_read_post` | Get a post by ID or slug |
| `ghost_add_post` | Create a new post |
| `ghost_edit_post` | Update an existing post |
| `ghost_delete_post` | Remove a post |
| `ghost_browse_tags` | List all tags |
| `ghost_add_tag` | Create a new tag |
| `ghost_browse_members` | List members |

## Managing the API Key

```bash
# View stored key
security find-generic-password -s "ghost-admin-api" -w

# Update key (delete old, add new)
security delete-generic-password -s "ghost-admin-api"
security add-generic-password -s "ghost-admin-api" -a "$USER" -w "NEW_KEY"
```

## Usage with Sermon Skills

Once configured, use with the sermon blog workflow:

```bash
# The --publish flag will use Ghost MCP to create a draft post
/sermon-to-blog https://youtube.com/watch?v=VIDEO_ID --publish
```

## Troubleshooting

### "Ghost Admin API key not found in Keychain"

Run the setup command:
```bash
security add-generic-password -s "ghost-admin-api" -a "$USER" -w "YOUR_KEY"
```

### "Invalid API key" error

- Ensure the key format is `{id}:{secret}` (includes the colon)
- Check the integration hasn't been deleted in Ghost Admin

### MCP server not loading

- Ensure Node.js 18+ is installed: `node --version`
- Check the wrapper script is executable: `chmod +x ghost-mcp-wrapper.sh`
- Test manually: `./ghost-mcp-wrapper.sh`

## Security

- API key is stored in macOS Keychain, not in plaintext files
- The wrapper script retrieves the key at runtime
- Never commit `.env` files or keys to git
