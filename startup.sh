#!/usr/bin/env bash
set -e

# Kill any existing Next.js dev server on port 8080
if lsof -ti:8080 >/dev/null 2>&1; then
  kill -9 "$(lsof -ti:8080)" 2>/dev/null || true
  sleep 1
fi

# Start the Next.js dev server on 0.0.0.0:8080
cd /workspace/console
npx next dev -p 8080 -H 0.0.0.0 &
NEXT_PID=$!

# Wait for the server to be ready
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:8080/ >/dev/null 2>&1; then
    echo "Console dev server is ready on port 8080"
    exit 0
  fi
  sleep 1
done

echo "Console dev server failed to start within 30s"
exit 1
