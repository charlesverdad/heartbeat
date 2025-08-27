# Multi-stage build for Living Life Bible Study Quiz
FROM node:22-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git python3 make g++

# Set working directory
WORKDIR /app

# Copy package files for dependency installation
COPY package.json yarn.lock ./

# Install all dependencies (including dev dependencies for building)
RUN yarn install --frozen-lockfile --network-timeout 600000

# Copy build configuration files
COPY vite.config.js tailwind.config.js postcss.config.js ./

# Copy source files
COPY src/ ./src/
COPY public/ ./public/
COPY index.html teacher.html ./
COPY questions-master.json test-config.json ./

# Build the frontend
RUN yarn build

# Production stage
FROM node:22-alpine AS production

# Install runtime dependencies
RUN apk add --no-cache \
    dumb-init \
    sqlite \
    && addgroup -g 1001 -S nodejs \
    && adduser -S quiz -u 1001 -G nodejs

# Set working directory
WORKDIR /app

# Copy package files and install production dependencies only
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --production --network-timeout 600000 \
    && yarn cache clean

# Copy built assets from builder stage
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/index.html ./
COPY --from=builder /app/teacher.html ./

# Copy application files
COPY server.js init-db.js ./
COPY questions-master.json test-config.json ./
COPY docker-entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Create data directory and set ownership
RUN mkdir -p /data && chown -R quiz:nodejs /app /data

# Switch to non-root user
USER quiz

# Environment variables
ENV NODE_ENV=production \
    PORT=3000 \
    DB_PATH=/data/quiz_data.db

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://localhost:$PORT/api/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

# Use dumb-init and run entrypoint
ENTRYPOINT ["dumb-init", "--"]
CMD ["./docker-entrypoint.sh"]
