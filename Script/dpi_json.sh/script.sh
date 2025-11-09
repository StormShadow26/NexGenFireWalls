#!/usr/bin/env bash
# ndpi_json_pretty.sh
# Pretty, colored, line-numbered JSON output for nDPI flows, with a waiting timer.
# Usage: sudo ./ndpi_json_pretty.sh [iface] [seconds]
# Example: sudo ./ndpi_json_pretty.sh wlp2s0 5

set -euo pipefail

IFACE="${1:-wlp2s0}"
DUR="${2:-5}"

command -v ndpiReader >/dev/null 2>&1 || { echo "ndpiReader not found." >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq not found. Install: sudo apt install jq" >&2; exit 1; }

# Prefer bat/batcat for gorgeous syntax highlighting if available
BAT_CMD=""
if command -v bat >/dev/null 2>&1; then
  BAT_CMD="bat --language json --paging=never --style=plain --color=always -n"
elif command -v batcat >/dev/null 2>&1; then
  BAT_CMD="batcat --language json --paging=never --style=plain --color=always -n"
fi

FIFO="$(mktemp -u)"
cleanup(){ [[ -p "$FIFO" ]] && rm -f "$FIFO"; }
trap cleanup EXIT
mkfifo "$FIFO"

# Start ndpiReader writing NDJSON to the FIFO; silence banners/stats to stderr
sudo ndpiReader -i "$IFACE" -s "$DUR" -v 2 -k /dev/stdout -K json 2>/dev/null > "$FIFO" &
READER_PID=$!

got_first=0
start_ts=$(date +%s)
flow_no=0

# Reader loop: consume the FIFO line by line; pretty-print only JSON lines
{
  while IFS= read -r line; do
    # skip any non-JSON chatter, accept only lines starting with '{'
    [[ "$line" =~ ^\{ ]] || continue

    if [[ $got_first -eq 0 ]]; then
      # clear the timer line
      printf "\r%*s\r" 80 " "
      got_first=1
    fi

    flow_no=$((flow_no+1))

    # Pretty-print the JSON with colors. If bat is present, let it do the highlighting.
    if [[ -n "$BAT_CMD" ]]; then
      # jq formats, bat highlights + line numbers
      printf '%s\n' "$line" | jq . | eval "$BAT_CMD"
    else
      # Fallback: jq color + classic line numbers
      printf '\n\033[2m// Flow %d\033[0m\n' "$flow_no"
      # -C keeps color escapes, pipe through nl for line numbers
      printf '%s\n' "$line" | jq -C . | nl -ba
    fi

    # Spacer between flows
    echo
  done
} < "$FIFO" &
CONSUMER_PID=$!

# Show a ticking timer until the first JSON arrives
while kill -0 "$CONSUMER_PID" 2>/dev/null; do
  [[ $got_first -eq 1 ]] && break
  elapsed=$(( $(date +%s) - start_ts ))
  printf "\r⏱  Waiting for flows… %ds" "$elapsed"
  sleep 1
done

wait "$READER_PID" 2>/dev/null || true
wait "$CONSUMER_PID" 2>/dev/null || true

