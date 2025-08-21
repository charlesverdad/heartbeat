#!/bin/sh
set -e

echo "🚀 Starting Living Life Bible Study application..."

# Environment variables with defaults
DB_PATH=${DB_PATH:-/data/quiz_data.db}
PORT=${PORT:-3000}
NODE_ENV=${NODE_ENV:-production}

echo "📊 Database path: $DB_PATH"
echo "🌐 Server port: $PORT"
echo "🔧 Environment: $NODE_ENV"

# Create data directory if it doesn't exist
mkdir -p "$(dirname "$DB_PATH")"

# Check if database exists and has tables (idempotent check)
if [ -f "$DB_PATH" ]; then
    echo "📋 Database file exists, checking if initialization is needed..."
    
    # Check if required tables exist using sqlite3 directly
    TABLES_COUNT=$(echo "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('quiz_submissions', 'student_answers', 'settings');" | sqlite3 "$DB_PATH" 2>/dev/null || echo "0")
    
    if [ "$TABLES_COUNT" = "3" ]; then
        echo "✅ Database already initialized (found $TABLES_COUNT/3 required tables)"
    else
        echo "🔧 Database exists but tables missing, initializing..."
        node init-db.js
    fi
else
    echo "🆕 Database file does not exist, creating and initializing..."
    node init-db.js
fi

echo "🎯 Starting quiz server..."

# Start the server
exec node server.js
