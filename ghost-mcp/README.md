# Ghost MCP Server Setup

MCP (Model Context Protocol) server for interacting with Ghost CMS, allowing Claude to create and manage blog posts.

## Prerequisites

- Ghost CMS instance with Admin API access
- Docker (for containerized deployment) OR Node.js 18+ (for local)
- Ghost Admin API key

## Getting Your Ghost Admin API Key

1. Log in to your Ghost Admin panel
2. Go to **Settings** → **Integrations**
3. Click **Add custom integration**
4. Name it something like "Claude MCP"
5. Copy the **Admin API Key** (format: `{id}:{secret}`)

## Option 1: Run with npx (Simplest)

No Docker needed - just run directly:

```bash
# Set environment variables
export GHOST_API_URL="https://heartbeatchurch.com.au"
export GHOST_ADMIN_API_KEY="your_admin_api_key"
export GHOST_API_VERSION="v5.0"

# Run the MCP server
npx @fanyangmeng/ghost-mcp
```

## Option 2: Docker Deployment

### Setup

```bash
cd ghost-mcp

# Copy and edit environment file
cp .env.example .env
# Edit .env with your Ghost credentials

# Build the image
docker build -t ghost-mcp .
```

### Run

```bash
# Run with docker-compose
docker-compose up -d

# Or run directly
docker run -it --env-file .env ghost-mcp
```

## Option 3: Claude Code MCP Configuration

Add to your `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ghost": {
      "command": "npx",
      "args": ["-y", "@fanyangmeng/ghost-mcp"],
      "env": {
        "GHOST_API_URL": "https://heartbeatchurch.com.au",
        "GHOST_ADMIN_API_KEY": "your_admin_api_key",
        "GHOST_API_VERSION": "v5.0"
      }
    }
  }
}
```

Or for Docker-based:

```json
{
  "mcpServers": {
    "ghost": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--env-file", "/path/to/ghost-mcp/.env", "ghost-mcp"]
    }
  }
}
```

## Available MCP Tools

Once configured, Claude can use these Ghost tools:

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
| `ghost_browse_newsletters` | List newsletters |

## Usage with Sermon Blog Skills

After configuring the MCP server, the `/sermon-to-blog` skill can publish directly to Ghost:

```bash
# Generate and publish sermon blog post
/sermon-to-blog https://youtube.com/watch?v=VIDEO_ID --publish
```

The `--publish` flag will:
1. Create a draft post in Ghost
2. Set the "Sermons" tag
3. Return the Ghost admin URL for review

## Troubleshooting

### "Invalid API key" error
- Ensure the key format is `{id}:{secret}` (includes the colon)
- Check the key hasn't been revoked in Ghost Admin

### "Connection refused" error
- Verify `GHOST_API_URL` is correct and accessible
- Check if Ghost is running and the URL includes `https://`

### MCP server not responding
- Ensure Node.js 18+ is installed
- Try running `npx @fanyangmeng/ghost-mcp` directly to see errors

## Security Notes

- Never commit `.env` files with real API keys
- The Admin API key has full access - keep it secure
- Consider using Ghost's built-in role permissions for limited access

## Sources

- [ghost-mcp on GitHub](https://github.com/MFYDev/ghost-mcp)
- [ghost-mcp on npm](https://www.npmjs.com/package/@fanyangmeng/ghost-mcp)
- [Ghost Admin API docs](https://ghost.org/docs/admin-api/)
