#!/bin/bash
# ==========================================================
# watch_blocked_ips.sh
# Monitors ndpi.db and prints new entries in blocked_ips table.
# ==========================================================

DB_PATH="ndpi.db"
LAST_COUNT=0

echo "🔍 Watching for new blocked IPs in $DB_PATH..."
echo "----------------------------------------------"

while true; do
    # Get the current count of rows
    CURRENT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM blocked_ips;")

    # If the count has increased, print the new entries
    if [ "$CURRENT_COUNT" -gt "$LAST_COUNT" ]; then
        echo ""
        echo "🚨 New entry detected at $(date '+%Y-%m-%d %H:%M:%S')"
        echo "----------------------------------------------"
        sqlite3 -header -column "$DB_PATH" "SELECT * FROM blocked_ips ORDER BY blocked_at DESC LIMIT 5;"
        echo "----------------------------------------------"
        LAST_COUNT=$CURRENT_COUNT
    fi

    # Sleep for a few seconds before checking again
    sleep 1
done
