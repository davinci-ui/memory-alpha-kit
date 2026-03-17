#!/bin/bash
# Guardian — restarts the watcher if it dies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCHER="$SCRIPT_DIR/realtime_watcher.py"
LOG_DIR="${LOG_DIR:-$HOME/.openclaw/logs}"
LOG="$LOG_DIR/watcher.log"
mkdir -p "$LOG_DIR"

while true; do
    if ! pgrep -f "realtime_watcher.py" > /dev/null; then
        echo "$(date): Guardian restarting watcher..." >> "$LOG"
        python3 "$WATCHER" >> "$LOG" 2>&1 &
    fi
    sleep 60
done
