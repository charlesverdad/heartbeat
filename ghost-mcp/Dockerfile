FROM node:20-alpine

WORKDIR /app

# Install the Ghost MCP server
RUN npm install -g @fanyangmeng/ghost-mcp

# Create a non-root user
RUN addgroup -g 1001 -S mcp && \
    adduser -S mcp -u 1001 -G mcp

USER mcp

# The MCP server communicates via stdio, so we use a wrapper
ENTRYPOINT ["npx", "@fanyangmeng/ghost-mcp"]
