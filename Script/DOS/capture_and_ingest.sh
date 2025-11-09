#!/bin/bash

# Interface and capture duration
INTERFACE="wlp2s0"
CAPTURE_TIME=2

while true; do
    timestamp=$(date +%Y%m%d_%H%M%S)
    output_file="ndpi_output_${timestamp}.json"

    echo "🔄 Capturing for ${CAPTURE_TIME} seconds to ${output_file}..."

    # Run ndpiReader but hide all its verbose output
    sudo ndpiReader -i "${INTERFACE}" -s "${CAPTURE_TIME}" -v 2 -k "${output_file}" -K json >/dev/null 2>&1

    echo "📊 Processing ${output_file} to database..."
    # Run collector.py and only show ingestion info
    python3 collector.py "${output_file}"

    # Show flow count in DB
    count=$(sqlite3 ndpi.db "SELECT COUNT(*) FROM flows;")
    echo "✅ Total flows in database: ${count}"

    # Optional cleanup
    rm -f "${output_file}"

    echo "⏳ Waiting 2 seconds before next capture..."
    sleep 2
done
