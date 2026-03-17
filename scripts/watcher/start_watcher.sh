#!/bin/bash
# Start the Memory Alpha realtime watcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${LOG_DIR:-$HOME/.openclaw/logs}"
mkdir -p "$LOG_DIR"

nohup python3 "$SCRIPT_DIR/realtime_watcher.py" \
    >> "$LOG_DIR/watcher.log" 2>&1 &
echo "$(date): Watcher started (pid $!)" >> "$LOG_DIR/watcher.log"
echo "Watcher started. Logs: $LOG_DIR/watcher.log"
