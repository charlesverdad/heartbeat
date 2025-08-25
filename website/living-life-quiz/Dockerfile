# Multi-stage build for Living Life Bible Study
FROM node:22.14.0-slim AS frontend-builder

# Set working directory for frontend build
WORKDIR /app

# Copy frontend package files
COPY package.json yarn.lock ./
COPY vite.config.js tailwind.config.js postcss.config.js ./

# Install frontend dependencies
RUN yarn install --frozen-lockfile

# Copy frontend source files
COPY src/ ./src/
COPY index.html ./
COPY teacher.html ./
COPY public/ ./public/
COPY questions-master.json ./
COPY test-config.json ./

# Build the frontend
RUN yarn build

# Production stage
FROM node:22.14.0-slim AS production

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    dumb-init \
    sqlite3 \
 && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 --gid 1001 quiz

# Copy questions and config files to app root
COPY questions-master.json ./
COPY test-config.json ./

# Copy built frontend assets from the builder stage to app root
COPY --from=frontend-builder /app/dist ./dist
COPY --from=frontend-builder /app/index.html ./
COPY --from=frontend-builder /app/teacher.html ./
COPY --from=frontend-builder /app/public ./public

# Create server directory and set it as working directory
WORKDIR /app/server

# Copy server package files and install dependencies
COPY server/package.json server/yarn.lock ./
RUN yarn install --frozen-lockfile --production && \
    yarn cache clean

# Copy server source files
COPY server/ ./

# Copy entrypoint script and make executable
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Create data directory and set permissions
RUN mkdir -p /data && \
    chown -R quiz:nodejs /app /data

# Switch to non-root user
USER quiz

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000
ENV DB_PATH=/data/quiz_data.db
ENV TEACHER_PASSWORD=admin123

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/api/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Run the entrypoint script
CMD ["./docker-entrypoint.sh"]
