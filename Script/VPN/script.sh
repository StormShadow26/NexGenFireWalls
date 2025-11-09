#!/usr/bin/env bash
set -euo pipefail

IFACE="${1:-wlp2s0}"
DUR="${2:-120}"

CSV_OUT="flows.csv"
JSON_OUT="flows.json"

# Terms to search (case-insensitive) and the label to print
declare -a TERMS=("Tor" "OpenVPN" "WireGuard" "Tailscale" "Forti" "UltraSurf" "OperaVPN" "IKE" "IPsec")
declare -a LABELS=("Tor" "OpenVPN" "WireGuard" "Tailscale" "Forti" "UltraSurf" "OperaVPN" "IKE" "IPsec")

command -v ndpiReader >/dev/null 2>&1 || { echo "ndpiReader not found"; exit 1; }

# Capture silently: CSV + JSON
sudo ndpiReader -i "$IFACE" -s "$DUR" -C "$CSV_OUT" -K json -k "$JSON_OUT" >/dev/null 2>&1 &
PID=$!

# Simple seconds timer
secs=0
printf "⏱ Capturing on %s for %ss\n" "$IFACE" "$DUR"
while kill -0 "$PID" 2>/dev/null; do
  printf "\r%4ss elapsed..." "$secs"
  sleep 1
  secs=$((secs+1))
done
printf "\r✅ Capture finished in %ss\n" "$secs"

# Pretty-print JSON like your screenshot
if [[ -f "$JSON_OUT" ]]; then
  echo "----- JSON flows (pretty) -----"
  if command -v jq >/dev/null 2>&1; then
    jq . "$JSON_OUT"
  else
    cat "$JSON_OUT"
  fi
else
  echo "⚠️  JSON output not found ($JSON_OUT)."
fi

# Presence-only detection (no details)
if [[ -f "$CSV_OUT" ]]; then
  any=false
  for i in "${!TERMS[@]}"; do
    term="${TERMS[$i]}"
    label="${LABELS[$i]}"
    if grep -qi -- "$term" "$CSV_OUT"; then
      echo "$label detected"
      any=true
    fi
  done
  if [[ "$any" == false ]]; then
    echo "Nothing detected"
  fi
else
  echo "⚠️  CSV output not found ($CSV_OUT)."
fi

