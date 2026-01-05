# Docker Deployment Guide

This document explains how to build and deploy the Living Life Bible Study application using Docker.

## Quick Start

### Using the Build Script

The easiest way to build the Docker image is using the provided build script:

```bash
# Build the image
./living-life-quiz

# Build with a specific version tag
./living-life-quiz v1.0.0
```

### Running the Container

After building, run the container:

```bash
# Create data directory for database persistence
mkdir -p data

# Run the container
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/data \
  --name living-life-quiz \
  living-life-quiz:latest
```

### Using Docker Compose (Recommended)

For easier management, use Docker Compose:

```bash
# Build and start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

## Configuration

The application can be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Port the server listens on |
| `DB_PATH` | `/data/quiz_data.db` | Path to SQLite database file |
| `TEACHER_PASSWORD` | `admin123` | Password for teacher portal access |
| `SESSION_SECRET` | `auto-generated` | Secret for session management |
| `NODE_ENV` | `production` | Node.js environment |

### Environment Variables Example

```bash
# Set environment variables before running
export TEACHER_PASSWORD="secure_password_123"
export SESSION_SECRET="your-very-long-session-secret-key"

# Run with custom configuration
docker run -d \
  -p 3000:3000 \
  -v $(pwd)/data:/data \
  -e TEACHER_PASSWORD="$TEACHER_PASSWORD" \
  -e SESSION_SECRET="$SESSION_SECRET" \
  -e DB_PATH="/data/quiz_data.db" \
  --name living-life-quiz \
  living-life-quiz:latest
```

## Database Persistence

The application uses SQLite for data storage. The database is mounted as a volume to ensure data persistence:

- **Container path**: `/data/quiz_data.db`
- **Host path**: `./data/quiz_data.db` (configurable)
- **Environment variable**: `DB_PATH`

### Database Initialization

The database is automatically initialized when the container starts:

- Creates required tables if they don't exist
- Adds default settings
- Creates performance indexes
- **Idempotent**: Safe to run multiple times

## Accessing the Application

Once running, the application is available at:

- **Student Portal**: http://localhost:3000
- **Teacher Portal**: http://localhost:3000/teacher
- **Health Check**: http://localhost:3000/api/health

## Monitoring

### Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker ps

# View detailed health status
docker inspect living-life-quiz | grep -A 10 "Health"
```

### Logs

View application logs:

```bash
# Follow logs
docker logs -f living-life-quiz

# View recent logs
docker logs --tail 50 living-life-quiz
```

## Development vs Production

### Development

For development, you can mount the source code:

```bash
docker run -d \
  -p 3000:3000 \
  -v $(pwd):/app \
  -v $(pwd)/data:/data \
  -e NODE_ENV=development \
  --name living-life-quiz-dev \
  living-life-quiz:latest
```

### Production

For production, use the standard configuration with proper secrets:

```bash
docker run -d \
  -p 3000:3000 \
  -v /path/to/persistent/data:/data \
  -e TEACHER_PASSWORD="$(openssl rand -base64 32)" \
  -e SESSION_SECRET="$(openssl rand -base64 64)" \
  --restart unless-stopped \
  --name living-life-quiz \
  living-life-quiz:latest
```

## Security Notes

1. **Change default passwords**: Always set a strong `TEACHER_PASSWORD` in production
2. **Use HTTPS**: Configure a reverse proxy (nginx/Apache) with SSL in production
3. **Session secrets**: Set a secure `SESSION_SECRET` in production
4. **Database access**: The database is only accessible from within the container
5. **Non-root user**: The application runs as a non-root user inside the container

## Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   # Use a different port
   docker run -p 3001:3000 ...
   ```

2. **Database permission errors**:
   ```bash
   # Ensure data directory has correct permissions
   chmod 755 data/
   ```

3. **Build failures**:
   ```bash
   # Clean Docker cache and rebuild
   docker system prune -f
   ./living-life-quiz
   ```

### Useful Commands

```bash
# Stop and remove container
docker stop living-life-quiz && docker rm living-life-quiz

# Rebuild image
docker build -t living-life-quiz:latest .

# Access container shell
docker exec -it living-life-quiz sh

# View container resource usage
docker stats living-life-quiz

# Backup database
docker cp living-life-quiz:/data/quiz_data.db ./backup_$(date +%Y%m%d_%H%M%S).db
```
